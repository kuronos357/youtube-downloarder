import os
import json
import re
import sys
import shutil
import pyperclip
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    def __init__(self, config_path, overrides=None):
        self.config_path = config_path
        self.data = self._read_json()
        if overrides:
            self.data.update(overrides)

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

    def _save_to_file(self):
        """(Private) Saves the current self.data to the config file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"設定の保存中にエラーが発生しました: {e}")
            raise

    def update_from_args_and_save(self, args):
        """Updates self.data from argparse args and saves to file."""
        updated = False
        
        # Top-level settings
        if args.quality and self.data.get('video_quality') != args.quality:
            self.data['video_quality'] = args.quality
            print(f"設定変更: video_quality -> {args.quality}")
            updated = True
        if args.dest_type and self.data.get('destination') != args.dest_type:
            self.data['destination'] = args.dest_type
            print(f"設定変更: destination -> {args.dest_type}")
            updated = True
        if args.no_notion and self.data.get('enable_notion_upload') is not False:
            self.data['enable_notion_upload'] = False
            print("設定変更: enable_notion_upload -> False")
            updated = True
        if args.no_log and self.data.get('enable_logging') is not False:
            self.data['enable_logging'] = False
            print("設定変更: enable_logging -> False")
            updated = True
        if args.no_watch and self.data.get('mark_as_watched') is not False:
            self.data['mark_as_watched'] = False
            print("設定変更: mark_as_watched -> False")
            updated = True

        # Determine the target index for directory-related updates
        target_index = self.data.get('default_directory_index', 0)
        valid_index_provided = False
        if args.index is not None:
            if 'directories' in self.data and 0 <= args.index < len(self.data['directories']):
                target_index = args.index
                valid_index_provided = True
            else:
                print(f"警告: インデックス {args.index} は無効です。ディレクトリ関連設定の保存はスキップされます。")

        # Update directory-related settings for the target profile
        if valid_index_provided and (args.format or args.output):
            profile = self.data['directories'][target_index]
            if args.format and profile.get('format') != args.format:
                profile['format'] = args.format
                print(f"プロファイル {target_index} のフォーマットを '{args.format}' に変更します。")
                updated = True
            if args.output and profile.get('path') != args.output:
                profile['path'] = args.output
                print(f"プロファイル {target_index} のパスを '{args.output}' に変更します。")
                updated = True

        # Update the default_directory_index itself if a valid one was provided
        if valid_index_provided and self.data.get('default_directory_index') != args.index:
            self.data['default_directory_index'] = args.index
            print(f"設定変更: default_directory_index -> {args.index}")
            updated = True

        if updated:
            try:
                self._save_to_file()
                print(f"設定を {self.config_path} に正常に保存しました。")
            except Exception:
                pass # Error is printed in _save_to_file
        else:
            print("指定された設定は既に適用済みか、引数が指定されなかったため、設定ファイルは更新されませんでした。")

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
            return []

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

class FileSorter:
    """ダウンロード後のファイルの仕分け、アップロード、ログ記録を処理するクラス"""
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, config, error_logger, notion_uploader):
        self.config = config
        self.error_logger = error_logger
        self.notion_uploader = notion_uploader
        self.destination = self.config.get('destination', 'local')
        self.jst = timezone(timedelta(hours=9), 'JST')
        
        self.gdrive_service = self._get_drive_service() if self.destination == 'gdrive' else None

    def process_downloads(self, download_results):
        """ダウンロード結果のリストを処理する"""
        is_playlist = len(download_results) > 1
        
        if is_playlist:
            self._process_playlist(download_results)
        elif download_results:
            self._process_single_file(download_results[0])

    def _process_single_file(self, result):
        """単一のダウンロード結果を処理する"""
        if not result['success']:
            self.error_logger.log(result['url'], result['error_message'])
            intended_path, _ = self._get_final_destination(result)
            log_entry = self._create_log_entry(result, intended_path)
            if self.notion_uploader:
                self.notion_uploader.upload(log_entry)
            return

        final_path, gdrive_folder_id = self._get_final_destination(result)
        
        try:
            final_path = self._sort_file(result['filepath'], final_path, gdrive_folder_id)
            self.error_logger.mark_as_resolved(result['url'])
            log_entry = self._create_log_entry(result, final_path)
            if self.notion_uploader:
                self.notion_uploader.upload(log_entry)
        except Exception as e:
            print(f"ファイルの仕分け中にエラーが発生しました: {e}")
            self.error_logger.log(result['url'], str(e))
            log_entry = self._create_log_entry(result, final_path, success=False, error_msg=str(e))
            if self.notion_uploader:
                self.notion_uploader.upload(log_entry)

    def _process_playlist(self, results):
        """再生リストのダウンロード結果を処理する"""
        playlist_info = results[0]['playlist_info']
        playlist_url = playlist_info['original_url']
        playlist_title = playlist_info.get('title', '再生リスト')

        final_playlist_dir, gdrive_folder_id = self._get_final_destination(results[0], is_playlist=True)
        
        if self.destination == 'gdrive' and self.config.get('create_playlist_folder', True):
             gdrive_folder_id = self._find_or_create_gdrive_folder(playlist_title, self.config.get('google_drive_parent_folder_id'))
        elif self.destination == 'local' and self.config.get('create_playlist_folder', True):
            final_playlist_dir = self._create_local_playlist_directory(final_playlist_dir, playlist_title)

        video_logs = []
        success_count = 0
        total_duration = 0
        error_messages = []

        for result in results:
            total_duration += result['info'].get('duration', 0)
            if not result['success']:
                self.error_logger.log(result['url'], result['error_message'])
                log = self._create_log_entry(result, final_playlist_dir)
                video_logs.append(log)
                if result['error_message']: error_messages.append(result['error_message'])
                continue

            try:
                self._sort_file(result['filepath'], final_playlist_dir, gdrive_folder_id)
                self.error_logger.mark_as_resolved(result['url'])
                log = self._create_log_entry(result, final_playlist_dir)
                video_logs.append(log)
                success_count += 1
            except Exception as e:
                print(f"ファイルの仕分け中にエラーが発生しました: {e}")
                self.error_logger.log(result['url'], str(e))
                log = self._create_log_entry(result, final_playlist_dir, success=False, error_msg=str(e))
                video_logs.append(log)
                error_messages.append(str(e))

        # 一時プレイリストディレクトリをクリーンアップします。動画のサブディレクトリは_sort_fileでクリーンアップされているはずです。
        try:
            if results and results[0].get('filepath'):
                # .../temp_downloads/PlaylistTitle/VideoTitle/file.mp4 のようなパスから PlaylistTitle ディレクトリを取得します
                video_dir = os.path.dirname(results[0]['filepath'])
                playlist_temp_dir = os.path.dirname(video_dir)
                
                # temp_downloads 内のディレクトリを削除していることを確認するための安全チェック
                if os.path.exists(playlist_temp_dir) and 'temp_downloads' in playlist_temp_dir:
                    playlist_title_from_info = results[0]['playlist_info'].get('title', 'playlist')
                    safe_title = re.sub(r'[\/*?:"<>|]', "_", playlist_title_from_info)
                    if os.path.basename(playlist_temp_dir) == safe_title:
                        print(f"一時プレイリストディレクトリをクリーンアップします: {playlist_temp_dir}")
                        shutil.rmtree(playlist_temp_dir)
                        print(f"クリーンアップ完了: {playlist_temp_dir}")
        except Exception as e:
            print(f"一時プレイリストディレクトリのクリーンアップに失敗しました: {e}")

        playlist_log = self._create_log_entry({
            'url': playlist_url,
            'info': {'title': f"{playlist_title} ({len(results)}件)", 'duration': total_duration},
            'format': results[0]['format'],
            'success': success_count == len(results),
            'error_message': '; '.join(error_messages)
        }, final_playlist_dir)

        if self.notion_uploader:
            print("\nNotionへのアップロードを開始します...")
            parent_page_id = self.notion_uploader.upload(playlist_log)
            if parent_page_id:
                print("各動画のログをサブアイテムとして登録します。")
                for v_log in video_logs:
                    self.notion_uploader.upload(v_log, parent_page_id=parent_page_id)

    def _get_final_destination(self, result, is_playlist=False):
        """設定に基づいて最終的な保存先パスまたはGdriveフォルダIDを取得する"""
        if self.destination == 'gdrive':
            parent_folder_id = self.config.get('google_drive_parent_folder_id')
            return parent_folder_id, parent_folder_id
        
        # ローカル保存の場合
        # コマンドラインからの出力先オーバーライドを優先
        if output_override := self.config.get('output_override'):
            if not os.path.isdir(output_override):
                print(f"警告: 指定された保存先ディレクトリが存在しません: {output_override}。作成を試みます。")
                try:
                    os.makedirs(output_override, exist_ok=True)
                    print(f"ディレクトリを作成しました: {output_override}")
                except Exception as e:
                    print(f"エラー: ディレクトリの作成に失敗しました: {e}。カレントディレクトリを使用します。")
                    return os.getcwd(), None
            return output_override, None

        directories = self.config.get('directories', [])
        default_index = self.config.get('default_directory_index', 0)
        
        if not (0 <= default_index < len(directories)):
            default_index = 0
            
        default_dir_info = directories[default_index]
        path = default_dir_info.get('path')
        
        if not os.path.isdir(path):
            print(f"警告: 保存先ディレクトリが存在しません: {path}。カレントディレクトリを使用します。")
            return os.getcwd(), None
            
        return path, None

    def _sort_file(self, temp_filepath, final_dest, gdrive_folder_id):
        """ファイルを最終目的地に移動またはアップロードし、一時ディレクトリをクリーンアップする"""
        if not os.path.exists(temp_filepath):
            return

        filename = os.path.basename(temp_filepath)
        final_path = ""

        if self.destination == 'gdrive':
            print(f"{filename} をGoogle Driveにアップロードしています...")
            upload_id = self._upload_to_gdrive(temp_filepath, gdrive_folder_id)
            if upload_id:
                print(f"ファイルID: {upload_id}。アップロードに成功しました。")
                final_path = f"gdrive:{gdrive_folder_id}/{filename}"
            else:
                raise Exception("Google Driveへのアップロードに失敗しました。")
        else: # ローカル保存
            final_path = os.path.join(final_dest, filename)
            print(f"{filename} を {final_dest} に移動しています...")
            shutil.move(temp_filepath, final_path)
            print("移動に成功しました。")

        # 動画用の一時ディレクトリをクリーンアップ
        try:
            video_temp_dir = os.path.dirname(temp_filepath)
            if os.path.exists(video_temp_dir) and 'temp_downloads' in video_temp_dir:
                print(f"一時ディレクトリをクリーンアップします: {video_temp_dir}")
                shutil.rmtree(video_temp_dir)
                print(f"クリーンアップ完了: {video_temp_dir}")
        except Exception as e:
            print(f"一時ディレクトリのクリーンアップに失敗しました: {e}")
        
        return final_path

    def _create_local_playlist_directory(self, base_dir, playlist_title):
        """ローカルに再生リスト用のディレクトリを作成する"""
        safe_title = re.sub(r'[\/*?:"<>|]', "_", playlist_title)
        playlist_dir = os.path.join(base_dir, safe_title)
        os.makedirs(playlist_dir, exist_ok=True)
        print(f"再生リスト用ディレクトリを作成: {playlist_dir}")
        return playlist_dir

    def _create_log_entry(self, result, output_path, success=None, error_msg=None):
        """Notionアップロード用のログエントリを作成する"""
        info = result.get('info', {})
        is_successful = result['success'] if success is None else success
        message = result['error_message'] if error_msg is None else error_msg

        quality_map = {"mp4": "video_quality", "webm": "video_quality", "mp3": "192kbps", "wav": "lossless", "flac": "lossless"}
        quality_key = quality_map.get(result['format'])
        quality = self.config.get(quality_key, 'best') if quality_key else 'best'

        return {
            "タイムスタンプ": datetime.now(self.jst).isoformat(),
            "URL": result['url'],
            "出力ディレクトリ": output_path,
            "形式": result['format'],
            "フォーマット": quality,
            "ファイル名": info.get('title', 'タイトル取得失敗'),
            "時間": info.get('duration'),
            "成否": is_successful,
            "エラーメッセージ": "" if is_successful else message
        }

    # --- Google Drive Methods ---
    def _get_drive_service(self):
        creds = None
        token_path = self.config.get('google_drive_token_path')
        credentials_path = self.config.get('google_drive_credentials_path')

        if token_path and os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            except Exception as e:
                print(f"トークンファイルの読み込みに失敗しました: {e}。再認証します。")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"トークンのリフレッシュに失敗しました: {e}。再認証します。")
                    creds = None
            
            if not creds:
                if not credentials_path or not os.path.exists(credentials_path):
                    msg = f"認証情報ファイルが見つかりません。パス: {credentials_path}"
                    print(f"エラー: {msg}")
                    self.error_logger.log("Google Drive Auth", msg)
                    return None
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    msg = f"認証フローの実行に失敗しました: {e}"
                    print(msg)
                    self.error_logger.log("Google Drive Auth", msg)
                    return None

            if creds and token_path:
                try:
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"トークンの保存に失敗しました: {e}")
        
        try:
            return build('drive', 'v3', credentials=creds)
        except HttpError as error:
            print(f'Driveサービスの構築中にエラーが発生しました: {error}')
            self.error_logger.log("Google Drive Auth", f"Failed to build service: {error}")
            return None

    def _upload_to_gdrive(self, file_path, folder_id):
        if not self.gdrive_service or not os.path.exists(file_path):
            print("Google Driveサービスが利用できないか、ファイルが存在しません。")
            return None

        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        
        try:
            file = self.gdrive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except HttpError as error:
            print(f'アップロード中にエラーが発生しました: {error}')
            self.error_logger.log(file_path, f"Google Drive upload failed: {error}")
            return None

    def _find_or_create_gdrive_folder(self, folder_name, parent_folder_id):
        if not self.gdrive_service:
            return parent_folder_id

        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
            response = self.gdrive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            if folders := response.get('files', []):
                print(f"既存のGoogle Driveフォルダを見つけました: '{folder_name}'")
                return folders[0].get('id')

            print(f"Google Driveフォルダを作成しています: '{folder_name}'...")
            file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
            folder = self.gdrive_service.files().create(body=file_metadata, fields='id').execute()
            print(f"フォルダを作成しました。ID: {folder.get('id')}")
            return folder.get('id')
        except HttpError as error:
            print(f'フォルダの検索または作成中にエラーが発生しました: {error}')
            self.error_logger.log(folder_name, f"Google Drive folder operation failed: {error}")
            return parent_folder_id

class YoutubeDownloader:
    """YouTube動画のダウンロードを処理するクラス"""
    def __init__(self, config, error_logger):
        self.config = config
        self.error_logger = error_logger

    def run(self, video_url, temp_dir, final_dest_display):
        """スクリプトのメイン処理を実行し、ダウンロード結果を返す"""
        if not video_url or "https" not in video_url:
            print("有効なURLが指定されていません。")
            return []

        _, format_choice = self._get_default_format()
        if not format_choice:
            return []

        try:
            ydl_opts = self._get_base_ydl_options()
            ydl_opts.update({'quiet': True, 'extract_flat': True, 'skip_download': True})
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            print(f"処理対象: {info.get('title', 'タイトル不明')}")
            print(f"URL: {video_url}")
            print(f"ダウンロードディレクトリ: {final_dest_display}")
            print(f"一時ディレクトリ: {temp_dir}")
            print(f"フォーマット: {format_choice}")

            if 'entries' in info and info.get('entries'):
                return self._process_playlist(info, temp_dir, format_choice)
            else:
                return [self._process_single_video(video_url, temp_dir, format_choice)]
        except Exception as e:
            clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            print(f"予期しないエラーが発生しました: {clean_error_msg}")
            self.error_logger.log(video_url, f"予期しないエラー: {clean_error_msg}")
            return []

    def _get_default_format(self):
        """デフォルトのフォーマットを取得する"""
        # コマンドラインからのオーバーライドを優先
        if format_override := self.config.get('format_override'):
            return None, format_override

        directories = self.config.get('directories', [])
        default_index = self.config.get('default_directory_index', 0)
        if not directories or not (0 <= default_index < len(directories)):
            print("フォーマット設定が見つかりません。")
            return None, None
        dir_info = directories[default_index]
        return dir_info.get('path'), dir_info.get('format')

    def _get_base_ydl_options(self):
        """認証や共通設定に関する基本的なyt-dlpオプションを生成する"""
        options = {}
        if (cookie_source := self.config.get('cookie_source')) == 'file':
            if cookie_file := self.config.get('cookie_file_path'):
                options['cookies'] = cookie_file
        elif cookie_source == 'browser':
            options['cookies-from-browser'] = self.config.get('cookie_browser', 'chrome')

        if self.config.get('mark_as_watched', False) and cookie_source != 'none':
            options['mark-watched'] = True
        return options

    def _get_download_options(self, dl_dir, format_choice):
        """yt-dlpのダウンロードオプションを生成する"""
        video_quality = self.config.get('video_quality', 'best')
        options = self._get_base_ydl_options()
        options.update({'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s')})

        if ffmpeg_path := self.config.get('ffmpeg_path'):
            options['ffmpeg_location'] = ffmpeg_path

        quality_selector = f"[height<=?{video_quality}]" if str(video_quality).isdigit() and video_quality != 'best' else ""
        postprocessors = []
        
        if format_choice in ["mp4", "webm"]:
            options['format'] = f'bestvideo{quality_selector}+bestaudio/best{quality_selector}/best'
            postprocessors.append({'key': 'FFmpegVideoConvertor', 'preferedformat': format_choice})
        elif format_choice in ["mp3", "wav", "flac"]:
            options['format'] = 'bestaudio/best'
            pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': format_choice}
            if format_choice == 'mp3': pp['preferredquality'] = '192'
            postprocessors.append(pp)
        else:
            options['format'] = 'best'

        if self.config.get('enable_volume_adjustment', False):
            volume_filter = ['volume', str(self.config.get('volume_level', 1.0))]
            options.setdefault('postprocessor_args', {}).setdefault('ffmpeg', []).extend(['-af'] + volume_filter)

        if postprocessors:
            options['postprocessors'] = postprocessors
        return options

    def _download_video(self, url, output_dir, format_choice):
        """指定されたURLの動画をダウンロードし、結果を辞書で返す"""
        print(f"\nダウンロード開始: {url}")

        # まず、ダウンロードせずに動画情報を取得してディレクトリを作成します
        info_opts = self._get_base_ydl_options()
        info_opts.update({'quiet': True, 'skip_download': True})
        try:
            with YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            print(f"✗ 動画情報の取得に失敗しました: {clean_error_msg}")
            self.error_logger.log(url, f"動画情報取得失敗: {clean_error_msg}")
            return {'success': False, 'error_message': f"動画情報取得失敗: {clean_error_msg}", 'info': {}, 'filepath': None, 'url': url, 'format': format_choice}

        # 動画固有の一時ディレクトリを作成
        video_title = info.get('title', 'untitled_video')
        safe_title = re.sub(r'[\/*?:"<>|]', "_", video_title)
        video_temp_dir = os.path.join(output_dir, safe_title)
        os.makedirs(video_temp_dir, exist_ok=True)
        print(f"一時ディレクトリを作成: {video_temp_dir}")

        ydl_opts = self._get_download_options(video_temp_dir, format_choice)
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                # info辞書を再利用してファイル名を予測
                temp_filepath = ydl.prepare_filename(info)
                base, _ = os.path.splitext(temp_filepath)
                final_filepath = f"{base}.{format_choice}"

                if os.path.exists(final_filepath):
                    msg = f"ファイルが既に存在: {os.path.basename(final_filepath)}"
                    print(f"ダウンロードを中止します: {msg}")
                    return {'success': False, 'error_message': msg, 'info': info, 'filepath': final_filepath, 'url': url, 'format': format_choice}

                ydl.download([url])
                print(f"✓ ダウンロード成功: {info.get('title', 'Unknown Title')}")
                return {'success': True, 'error_message': None, 'info': info, 'filepath': final_filepath, 'url': url, 'format': format_choice}
            except Exception as e:
                clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
                print(f"✗ エラーが発生しました: {clean_error_msg}")
                # 事前に取得したinfo辞書があります
                return {'success': False, 'error_message': clean_error_msg, 'info': info, 'filepath': None, 'url': url, 'format': format_choice}

    def _process_single_video(self, url, output_dir, format_choice):
        """単一動画のダウンロード処理"""
        print("個別動画をダウンロードしています...")
        return self._download_video(url, output_dir, format_choice)

    def _process_playlist(self, info, output_dir, format_choice):
        """再生リストのダウンロード処理"""
        results = []
        video_urls = [entry['url'] for entry in info.get('entries', []) if 'url' in entry]
        
        if not video_urls:
            print("再生リストから動画URLを取得できませんでした。")
            return [{'success': False, 'error_message': "再生リストからURL取得失敗", 'info': info, 'filepath': None, 'url': info['original_url'], 'format': format_choice}]

        playlist_dir = self._create_temp_playlist_directory(output_dir, info.get('title', 'playlist'))
        
        # ThreadPoolExecutorを使用して並列ダウンロードを実行
        with ThreadPoolExecutor(max_workers=4) as executor: # 4つの並列ワーカーを使用。これは後で設定可能にできます。
            futures = {executor.submit(self._download_video, url, playlist_dir, format_choice): url for url in video_urls}
            
            for i, future in enumerate(as_completed(futures), 1):
                url = futures[future]
                print(f"\n再生リストの処理中 ({i}/{len(video_urls)}): {url}")
                try:
                    result = future.result()
                    result['playlist_info'] = info
                    results.append(result)
                except Exception as exc:
                    print(f'✗ {url} のダウンロードで例外が発生しました: {exc}')
                    # エラーをログに記録
                    clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(exc))
                    self.error_logger.log(url, f"並列処理中の例外: {clean_error_msg}")
                    # 再生リストの処理の一貫性を保つために失敗結果を作成
                    results.append({
                        'success': False, 
                        'error_message': clean_error_msg, 
                        'info': {}, # 例外が早期に発生した場合、infoが利用できない可能性があります
                        'filepath': None, 
                        'url': url, 
                        'format': format_choice,
                        'playlist_info': info
                    })

        return results

    def _create_temp_playlist_directory(self, base_dir, playlist_title):
        """一時的な再生リスト用のディレクトリを作成する"""
        safe_title = re.sub(r'[\/*?:"<>|]', "_", playlist_title)
        playlist_dir = os.path.join(base_dir, safe_title)
        os.makedirs(playlist_dir, exist_ok=True)
        print(f"一時的な再生リスト用ディレクトリを作成: {playlist_dir}")
        return playlist_dir

def print_summary(results):
    """処理結果のサマリを表示する"""
    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    failed_count = total - success_count
    
    print(f"\n{'='*50}")
    print("処理完了！")
    print(f"総数: {total}, 成功: {success_count}, 失敗: {failed_count}")
    if failed_count > 0:
        print(f"⚠️ {failed_count}件の処理に失敗しました。")
    else:
        print("✓ すべての処理が完了しました。")
    print(f"{'='*50}")

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="YouTube動画をダウンロードし、整理します。")
    parser.add_argument("url", nargs='?', default=None, help="ダウンロードする動画または再生リストのURL。指定しない場合はクリップボードから取得します。")
    parser.add_argument("-f", "--format", choices=['mp4', 'webm', 'mp3', 'wav', 'flac'], help="ダウンロード形式を指定します。")
    parser.add_argument("-q", "--quality", help="動画の品質を指定します (例: 1080, 720, best)。")
    parser.add_argument("-o", "--output", help="保存先のディレクトリパスを指定します。")
    parser.add_argument("-i", "--index", type=int, help="使用するディレクトリプロファイルのインデックス番号を指定します。")
    parser.add_argument("--dest-type", choices=['local', 'gdrive'], help="保存先種別（ローカル or Google Drive）を指定します。")
    parser.add_argument("--no-notion", action="store_true", help="Notionへのアップロードを無効にします。")
    parser.add_argument("--no-log", action="store_true", help="ローカルのエラーログ記録を無効にします。")
    parser.add_argument("--no-watch", action="store_true", help="YouTubeで「視聴済み」としてマークする機能を無効にします。")
    parser.add_argument("--save", action="store_true", help="指定した引数を設定ファイルに保存します。")
    parser.add_argument("--show-config", action="store_true", help="現在の設定を表示して終了します。")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    config_path = base_dir / '設定・履歴/config.json'

    if args.show_config:
        print(f"--- 現在の設定ファイル ({config_path}) の内容 ---")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print(json.dumps(config_data, indent=2, ensure_ascii=False))
        except FileNotFoundError:
            print("エラー: 設定ファイルが見つかりません。")
        except json.JSONDecodeError:
            print("エラー: 設定ファイルが破損しているか、JSON形式ではありません。")
        return

    # --saveフラグが指定された場合、設定を保存
    if args.save:
        print("設定をconfig.jsonに保存します...")
        config_to_save = Config(config_path)
        config_to_save.update_from_args_and_save(args)

    video_url = args.url
    if not video_url:
        # --saveが使用された場合、URLなしでもエラーにせず終了
        if args.save:
            print("設定の保存が完了しました。URLが指定されていないため、ダウンロードは行いません。")
            return
        
        video_url = pyperclip.paste()
        print("コマンドライン引数にURLが指定されていないため、クリップボードからURLを取得しました。")

    if not video_url or "https" not in video_url:
        print("有効なURLが指定されていません。")
        return

    # 一時的な上書き設定を作成
    overrides = {
        'format_override': args.format,
        'output_override': args.output,
        'video_quality': args.quality,
        'destination': args.dest_type,
        'default_directory_index': args.index,
    }
    if args.no_notion:
        overrides['enable_notion_upload'] = False
    if args.no_log:
        overrides['enable_logging'] = False
    if args.no_watch:
        overrides['mark_as_watched'] = False
    
    overrides = {k: v for k, v in overrides.items() if v is not None}

    temp_dir = base_dir / 'temp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    
    config = Config(config_path, overrides)
    
    # 表示用の最終的な保存先を取得
    final_dest_display = config.get('output_override')
    if not final_dest_display:
        if config.get('destination') == 'gdrive':
            final_dest_display = 'Google Drive'
        else:
            dirs = config.get('directories', [])
            idx = config.get('default_directory_index', 0)
            if 0 <= idx < len(dirs):
                final_dest_display = dirs[idx].get('path', '（不明）')
            else:
                final_dest_display = '（不明）'

    error_logger = ErrorLogger(config)
    
    downloader = YoutubeDownloader(config, error_logger)
    download_results = downloader.run(video_url, temp_dir, final_dest_display)

    if not download_results:
        print("ダウンロード対象がありませんでした。")
        return

    notion_uploader = NotionUploader(config, error_logger) if config.get('enable_notion_upload') else None
    sorter = FileSorter(config, error_logger, notion_uploader)
    
    sorter.process_downloads(download_results)
    
    print_summary(download_results)

if __name__ == "__main__":
    main()
