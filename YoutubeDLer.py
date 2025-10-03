import os
import json
import re
import sys
import pyperclip
import requests
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

class Config:
    """設定ファイルから設定を読み込み、管理するクラス"""
    def __init__(self, config_path):
        self.config_path = config_path
        self.data = self._read_json()

    def _read_json(self):
        """JSONファイルを読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")
            return {}

    def get(self, key, default=None):
        """設定値を取得する"""
        return self.data.get(key, default)

class NotionUploader:
    """Notionデータベースへのログエントリのアップロードを処理するクラス"""
    def __init__(self, config, error_logger):
        self.config = config
        self.error_logger = error_logger
        self.enabled = self.config.get('enable_notion_upload', False)
        self.api_key = self.config.get('notion_api_key')
        self.database_id = self.config.get('notion_database_id')

    def upload(self, log_entry, parent_page_id=None):
        """Notionデータベースにログエントリをアップロードする"""
        if not self.enabled:
            return None

        print(f"ログエントリをNotionデータベースにアップロード... ファイル名: {log_entry.get('ファイル名', 'N/A')}")

        if not self.api_key or not self.database_id:
            error_msg = "NotionのAPIキーまたはデータベースIDがconfig.jsonに設定されていません。"
            print(error_msg)
            self.error_logger.log(log_entry.get("URL"), error_msg)
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        properties = self._create_properties(log_entry, parent_page_id)
        payload = {"parent": {"database_id": self.database_id}, "properties": properties}

        try:
            response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            response.raise_for_status()
            page_id = response.json().get("id")
            print(f"ログをNotionにアップロードしました。 Page ID: {page_id}")
            return page_id
        except requests.exceptions.RequestException as e:
            error_message = f"Notionへのアップロードに失敗しました: {e}"
            if e.response:
                error_message += f" | Response: {e.response.text}"
            print(error_message)
            self.error_logger.log(log_entry.get("URL"), error_message)
            return None

    def _create_properties(self, log_entry, parent_page_id=None):
        """Notionページのプロパティを作成する"""
        properties = {
            "ファイル名": {"title": [{"text": {"content": log_entry.get("ファイル名", "N/A")}}]},
            "URL": {"url": log_entry.get("URL")},
            "出力ディレクトリ": {"rich_text": [{"text": {"content": log_entry.get("出力ディレクトリ", "")}}]},
            "形式": {"select": {"name": log_entry.get("形式", "")}} ,
            "フォーマット": {"select": {"name": str(log_entry.get("フォーマット", ""))}},
            "タイムスタンプ": {"date": {"start": log_entry.get("タイムスタンプ")}},
            "成否": {"checkbox": log_entry.get("成否", False)},
            "エラーメッセージ": {"rich_text": [{"text": {"content": log_entry.get("エラーメッセージ", "")}}]}
        }
        if (duration_seconds := log_entry.get("時間")) is not None:
            properties["時間"] = {"number": int(duration_seconds / 60)}
        if parent_page_id:
            properties["親アイテム"] = {"relation": [{"id": parent_page_id}]}
        return properties

class GoogleDriveUploader:
    """Handles uploading files to Google Drive."""
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, config, error_logger):
        self.config = config
        self.error_logger = error_logger
        self.enabled = self.config.get('destination') == 'gdrive'
        self.credentials_path = self.config.get('google_drive_credentials_path')
        self.token_path = self.config.get('google_drive_token_path')
        self.parent_folder_id = self.config.get('google_drive_parent_folder_id')
        self.service = self._get_drive_service()

    def _get_drive_service(self):
        if not self.enabled:
            return None
        
        creds = None
        if self.token_path and os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception as e:
                print(f"トークンファイルの読み込みに失敗しました: {e}。再認証します。")
                creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"トークンのリフレッシュに失敗しました: {e}。再認証します。")
                    creds = None # Force re-authentication
            
            if not creds:
                if not self.credentials_path or not os.path.exists(self.credentials_path):
                    print("エラー: Google Driveの認証情報ファイルが見つかりません。")
                    self.error_logger.log("Google Drive Auth", f"認証情報ファイルが見つかりません。パス: {self.credentials_path}")
                    return None
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"認証フローの実行に失敗しました: {e}")
                    self.error_logger.log("Google Drive Auth", f"認証フローの実行に失敗しました: {e}")
                    return None

            if creds and self.token_path:
                try:
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"トークンの保存に失敗しました: {e}")
        
        try:
            return build('drive', 'v3', credentials=creds)
        except HttpError as error:
            print(f'An error occurred building Drive service: {error}')
            self.error_logger.log("Google Drive Auth", f"Failed to build service: {error}")
            return None

    def upload_file(self, file_path, folder_id=None):
        if not self.service or not os.path.exists(file_path):
            print("Google Drive service not available or file does not exist.")
            return None

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id or self.parent_folder_id]
        }
        
        if not (folder_id or self.parent_folder_id):
            print("Error: Google Drive parent folder ID is not set.")
            self.error_logger.log(file_path, "Google Drive parent folder ID is not set.")
            return None

        media = MediaFileUpload(file_path, resumable=True)
        
        try:
            print(f"Uploading {os.path.basename(file_path)} to Google Drive...")
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"File ID: {file.get('id')}. Upload successful.")
            return file.get('id')
        except HttpError as error:
            print(f'An error occurred during upload: {error}')
            self.error_logger.log(file_path, f"Google Drive upload failed: {error}")
            return None

    def find_or_create_folder(self, folder_name):
        if not self.service:
            return self.parent_folder_id

        try:
            # Search for the folder first
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{self.parent_folder_id}' in parents and trashed=false"
            response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            folders = response.get('files', [])
            if folders:
                print(f"Found existing Google Drive folder: '{folder_name}'")
                return folders[0].get('id')

            # If not found, create it
            print(f"Creating Google Drive folder: '{folder_name}'...")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.parent_folder_id]
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            print(f"Folder created with ID: {folder.get('id')}")
            return folder.get('id')
        except HttpError as error:
            print(f'An error occurred while finding/creating folder: {error}')
            self.error_logger.log(folder_name, f"Google Drive folder operation failed: {error}")
            return self.parent_folder_id # Fallback to parent


class ErrorLogger:
    """エラー情報をローカルのJSONファイルに記録するクラス"""
    def __init__(self, config):
        self.config = config
        self.enabled = self.config.get('enable_logging', True)
        self.log_file_path = self.config.get('log_file_path')
        self.jst = timezone(timedelta(hours=9), 'JST')

    def log(self, url, error_message):
        """エラー情報を記録する"""
        if not self.enabled or not self.log_file_path:
            return

        new_log_entry = {
            "タイムスタンプ": datetime.now(self.jst).isoformat(),
            "URL": url,
            "エラーメッセージ": error_message,
            "解決済み": False
        }

        logs = self._read_logs()
        if any(log.get("URL") == url and not log.get("解決済み") for log in logs):
            print(f"未解決の既存エラーログがあるため、新規ログは追加しません: {url}")
            return

        logs.append(new_log_entry)
        self._write_logs(logs)
        print(f"エラーログを書き込みました: {url}")

    def mark_as_resolved(self, url):
        """指定されたURLのエラーログを「解決済み」に更新する"""
        if not self.enabled or not self.log_file_path or not os.path.exists(self.log_file_path):
            return

        logs = self._read_logs()
        updated = False
        for log in logs:
            if log.get("URL") == url and not log.get("解決済み"):
                log["解決済み"] = True
                updated = True

        if updated:
            self._write_logs(logs)
            print(f"エラーログを「解決済み」に更新しました: {url}")

    def _read_logs(self):
        """ログファイルを読み込む"""
        if not os.path.exists(self.log_file_path):
            return []
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # ファイルが空、壊れている、または見つからない場合は、新しい空のリストを返す
            return []

        # ログファイルは常にリスト形式であるべき
        if isinstance(data, list):
            return data
        
        print("警告: ログファイルが予期しない形式（リストではない）です。ログを初期化します。")
        return []

    def _write_logs(self, logs):
        """ログファイルに書き込む"""
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"エラーログの書き込み/更新に失敗しました: {e}")

class YoutubeDownloader:
    """YouTube動画のダウンロードを処理するクラス"""
    def __init__(self, config, notion_uploader, error_logger, gdrive_uploader):
        self.config = config
        self.notion_uploader = notion_uploader
        self.error_logger = error_logger
        self.gdrive_uploader = gdrive_uploader
        self.jst = timezone(timedelta(hours=9), 'JST')

    def get_download_options(self, dl_dir, format_choice):
        """yt-dlpのダウンロードオプションを生成する"""
        print("ダウンロードオプションを取得しています...")
        video_quality = self.config.get('video_quality', 'best')
        enable_volume_adjustment = self.config.get('enable_volume_adjustment', False)
        volume_level = self.config.get('volume_level', 1.0)

        options = {
            'outtmpl': os.path.join(dl_dir, f'%(title)s.%(ext)s'),
        }

        # ffmpegのパスとクッキーを設定
        ffmpeg_path = self.config.get('ffmpeg_path')
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            options['ffmpeg_location'] = ffmpeg_path
        if self.config.get('use_cookies', False):
            options['cookies-from-browser'] = self.config.get('cookie_browser', 'chrome')

        # フォーマットと品質を設定
        quality_selector = f"[height<=?{video_quality}]" if str(video_quality).isdigit() and video_quality != 'best' else ""
        
        postprocessors = []
        
        if format_choice in ["mp4", "webm"]:
            options['format'] = f'bestvideo{quality_selector}+bestaudio/best{quality_selector}/best'
            pp = {'key': 'FFmpegVideoConvertor', 'preferedformat': format_choice}
            postprocessors.append(pp)
        elif format_choice in ["mp3", "wav", "flac"]:
            options['format'] = 'bestaudio/best'
            pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': format_choice}
            if format_choice == 'mp3':
                pp['preferredquality'] = '192'
            postprocessors.append(pp)
        else:
            options['format'] = 'best'

        # 音量調整
        if enable_volume_adjustment:
            volume_filter = ['-af', f'volume={volume_level}']
            # 既存のffmpegポストプロセッサーがあれば、それにフィルターを追加する
            if postprocessors and postprocessors[0]['key'].startswith('FFmpeg'):
                postprocessors[0].setdefault('params', []).extend(volume_filter)
            else:
                # なければ、音量調整のためだけに新しいポストプロセッサーを追加する
                postprocessors.append({'key': 'FFmpegPostProcessor', 'params': volume_filter})

        if postprocessors:
            options['postprocessors'] = postprocessors
        
        return options

    def download_video(self, url, output_dir, format_choice):
        """指定されたURLの動画をダウンロードし、結果を返す"""
        print("ダウンロード開始")
        ydl_opts = self.get_download_options(output_dir, format_choice)
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                temp_filepath = ydl.prepare_filename(info)
                base_filename = os.path.splitext(os.path.basename(temp_filepath))[0]
                final_filename = f"{base_filename}.{format_choice}"
                final_filepath = os.path.join(output_dir, final_filename)

                if os.path.exists(final_filepath):
                    msg = f"ファイルが既に存在: {final_filename}"
                    print(f"ダウンロードを中止します: {msg}")
                    return False, msg, info, final_filepath

                ydl.download([url])
                print(f"✓ ダウンロード成功: {info.get('title', 'Unknown Title')}")
                return True, None, info, final_filepath
            except Exception as e:
                clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
                print(f"✗ エラーが発生しました: {clean_error_msg}")
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception:
                    info = None
                return False, clean_error_msg, info, None

    def run(self):
        """スクリプトのメイン処理を実行する"""
        if len(sys.argv) > 1:
            video_url = sys.argv[1]
            print("コマンドライン引数からURLを取得しました。")
        else:
            video_url = pyperclip.paste()
            print("クリップボードからURLを取得しました。")

        if not video_url or "https" not in video_url:
            print("有効なURLが指定されていません。")
            return

        output_dir, format_choice = self._get_default_settings()
        if not output_dir or not format_choice:
            return

        try:
            # 先に動画情報を取得してタイトルを表示
            ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
            if self.config.get('use_cookies', False):
                ydl_opts['cookies-from-browser'] = self.config.get('cookie_browser', 'chrome')
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            title = info.get('title', 'タイトル不明')
            print(f"処理対象: {title}")
            print(f"URL: {video_url}")

            destination = self.config.get('destination', 'local')
            if destination == 'gdrive':
                gdrive_folder_id = self.gdrive_uploader.parent_folder_id
                print(f"保存先: Google Drive (フォルダID: {gdrive_folder_id})")
            else:
                print(f"保存先: ローカル ({output_dir})")
            print(f"フォーマット: {format_choice}")
            
            is_playlist = 'entries' in info and info.get('entries')
            if is_playlist:
                self._process_playlist(info, video_url, output_dir, format_choice)
            else:
                self._process_single_video(video_url, output_dir, format_choice)
        except Exception as e:
            print(f"処理対象URL: {video_url}")
            clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            print(f"予期しないエラーが発生しました: {clean_error_msg}")
            self.error_logger.log(video_url, f"予期しないエラー: {clean_error_msg}")

    def _get_default_settings(self):
        """デフォルトの保存先とフォーマットを取得する"""
        directories = self.config.get('directories', [])
        default_index = self.config.get('default_directory_index', 0)
        
        if not directories:
            print("ディレクトリが設定されていません。")
            return None, None
        
        if not (0 <= default_index < len(directories)):
            default_index = 0
            
            
        default_dir_info = directories[default_index]
        path = default_dir_info.get('path')
        if not os.path.isdir(path):
            print(f"保存先ディレクトリが存在しません: {path}")
            return None, None
            
        return path, default_dir_info.get('format')

    def _process_single_video(self, url, output_dir, format_choice):
        """単一動画のダウンロード処理"""
        print("個別動画をダウンロードしています...")
        success, error_msg, video_info, final_filepath = self.download_video(url, output_dir, format_choice)
        
        if success:
            self.error_logger.mark_as_resolved(url)
            if self.gdrive_uploader.enabled and final_filepath:
                upload_id = self.gdrive_uploader.upload_file(final_filepath)
                if upload_id:
                    try:
                        os.remove(final_filepath)
                        print(f"ローカルファイルを削除しました: {final_filepath}")
                    except OSError as e:
                        print(f"ローカルファイルの削除に失敗しました: {e}")
        else:
            self.error_logger.log(url, error_msg)

        log_entry = self._create_log_entry(url, output_dir, format_choice, success, error_msg, video_info)
        self.notion_uploader.upload(log_entry)
        self._print_summary(1, 1 if success else 0, 1 if not success else 0)

    def _process_playlist(self, info, playlist_url, output_dir, format_choice):
        """再生リストのダウンロード処理"""
        video_urls = [entry['url'] for entry in info.get('entries', []) if 'url' in entry]
        if not video_urls:
            print("再生リストから動画URLを取得できませんでした。")
            self.error_logger.log(playlist_url, "再生リストからURL取得失敗")
            self._print_summary(1, 0, 1)
            return

        playlist_title = info.get('title', '再生リスト')
        local_output_dir = self._create_playlist_directory(output_dir, playlist_title)
        
        gdrive_folder_id = None
        if self.gdrive_uploader.enabled:
            if self.config.get('google_drive_create_playlist_folder', True):
                gdrive_folder_id = self.gdrive_uploader.find_or_create_folder(playlist_title)
            else:
                gdrive_folder_id = self.gdrive_uploader.parent_folder_id

        stats = {'total': len(video_urls), 'success': 0, 'failed': 0}
        playlist_duration = 0
        error_messages = []
        video_logs = []

        for i, url in enumerate(video_urls, 1):
            print(f"\nダウンロード中 ({i}/{stats['total']}): ")
            success, error_msg, video_info, final_filepath = self.download_video(url, local_output_dir, format_choice)
            
            duration = video_info.get('duration') if video_info else 0
            playlist_duration += duration
            
            video_log = self._create_log_entry(url, local_output_dir, format_choice, success, error_msg, video_info)
            video_logs.append(video_log)

            if success:
                stats['success'] += 1
                self.error_logger.mark_as_resolved(url)
                if self.gdrive_uploader.enabled and final_filepath:
                    upload_id = self.gdrive_uploader.upload_file(final_filepath, folder_id=gdrive_folder_id)
                    if upload_id:
                        try:
                            os.remove(final_filepath)
                            print(f"ローカルファイルを削除しました: {final_filepath}")
                        except OSError as e:
                            print(f"ローカルファイルの削除に失敗しました: {e}")
            else:
                stats['failed'] += 1
                if error_msg: error_messages.append(error_msg)
                self.error_logger.log(url, error_msg)

        playlist_log = self._create_log_entry(
            playlist_url, local_output_dir, format_choice, stats['failed'] == 0,
            '; '.join(error_messages),
            {'title': f"{playlist_title} ({stats['total']}件)", 'duration': playlist_duration}
        )
        
        if self.notion_uploader.enabled:
            print("\nNotionへのアップロードを開始します...")
            parent_page_id = self.notion_uploader.upload(playlist_log)
            if parent_page_id:
                print("各動画のログをサブアイテムとして登録します。")
                for v_log in video_logs:
                    self.notion_uploader.upload(v_log, parent_page_id=parent_page_id)

        self._print_summary(stats['total'], stats['success'], stats['failed'])

    def _create_playlist_directory(self, base_dir, playlist_title):
        """再生リスト用のディレクトリを作成する"""
        if not self.config.get('makedirector', True):
            return base_dir
        safe_title = re.sub(r'[\\/*?:\"<>|]', "_", playlist_title)
        playlist_dir = os.path.join(base_dir, safe_title)
        os.makedirs(playlist_dir, exist_ok=True)
        print(f"再生リスト用ディレクトリを作成: {playlist_dir}")
        return playlist_dir

    def _create_log_entry(self, url, output_dir, format_choice, success, error_msg, video_info):
        """Notionアップロード用のログエントリを作成する"""
        info = video_info or {}
        quality_map = {"mp4": "video_quality", "webm": "video_quality", "mp3": "192kbps", "wav": "lossless", "flac": "lossless"}
        quality_key = quality_map.get(format_choice)
        quality = self.config.get(quality_key, 'best') if quality_key else 'best'

        return {
            "タイムスタンプ": datetime.now(self.jst).isoformat(),
            "URL": url,
            "出力ディレクトリ": output_dir,
            "形式": format_choice,
            "フォーマット": quality,
            "ファイル名": info.get('title', 'タイトル取得失敗'),
            "時間": info.get('duration'),
            "成否": success,
            "エラーメッセージ": "" if success else error_msg
        }

    def _print_summary(self, total, success, failed):
        """ダウンロード結果のサマリを表示する"""
        print(f"\n{'='*50}")
        print("ダウンロード完了！")
        print(f"総数: {total}, 成功: {success}, 失敗: {failed}")
        if failed > 0:
            print(f"⚠️ {failed}件のダウンロードに失敗しました。")
        else:
            print("✓ すべてのダウンロードが完了しました。")
        print(f"{'='*50}")

def main():
    """メイン処理"""
    config_path = Path(__file__).parent / '設定・履歴/config.json'
    
    config = Config(config_path)
    error_logger = ErrorLogger(config)
    notion_uploader = NotionUploader(config, error_logger)
    gdrive_uploader = GoogleDriveUploader(config, error_logger)
    downloader = YoutubeDownloader(config, notion_uploader, error_logger, gdrive_uploader)
    
    downloader.run()

if __name__ == "__main__":
    main()