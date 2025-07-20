import os
import json
import re
import pyperclip
import requests
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 設定ファイルのパスを定義
file_path = Path(__file__).parent / '設定・履歴/config.json'

def read_json(file_path):
    """JSONファイルを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

# 設定データを読み込む
data = read_json(file_path)

# セッション情報を保持するグローバル変数
session_info = {}

def initialize_session(url, output_dir, format_choice, quality):
    """ダウンロードセッションの情報を初期化する"""
    global session_info
    jst = timezone(timedelta(hours=9), 'JST') # 日本標準時
    session_info = {
        "タイムスタンプ": datetime.now(jst).isoformat(),
        "URL": url,
        "出力ディレクトリ": output_dir,
        "形式": format_choice,
        "フォーマット": quality,
        "ファイル名": "",
        "成否": False,
        "エラーメッセージ": ""
    }

def update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages=None, filenames=None):
    """ダウンロードセッションの結果を更新する"""
    print("セッション終了時に結果を更新")
    global session_info
    
    # ファイル名を設定（複数ある場合は「他X件」と表示）
    if filenames and len(filenames) > 0:
        if len(filenames) == 1:
            session_info["ファイル名"] = filenames[0]
        else:
            session_info["ファイル名"] = f"{filenames[0]} 他{len(filenames)-1}件"
    elif failed_downloads > 0:
        # 失敗時にファイル名が取得できなかった場合はURLをファイル名として使用
        session_info["ファイル名"] = session_info.get("URL", "タイトル取得失敗")

    # 成功/失敗とエラーメッセージを設定
    is_success = failed_downloads == 0
    session_info["成否"] = is_success
    if not is_success and error_messages:
        session_info["エラーメッセージ"] = '; '.join(error_messages)
    else:
        session_info["エラーメッセージ"] = ""

def upload_to_notion(log_entry, parent_page_id=None):
    """Notionデータベースにログエントリをアップロードする"""
    print(f"ログエントリをNotionデータベースにアップロード... ファイル名: {log_entry.get('ファイル名', 'N/A')}")

    if not data.get('enable_notion_upload', False):
        return None

    api_key = data.get('notion_api_key')
    database_id = data.get('notion_database_id')

    if not api_key or not database_id:
        print("NotionのAPIキーまたはデータベースIDがconfig.jsonに設定されていません。")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Notionページのプロパティを作成
    properties = {
        "ファイル名": {"title": [{"text": {"content": log_entry.get("ファイル名", "N/A")}}]},
        "URL": {"url": log_entry.get("URL")},
        "出力ディレクトリ": {"rich_text": [{"text": {"content": log_entry.get("出力ディレクトリ", "")}}]},
        "形式": {"select": {"name": log_entry.get("形式", "")}},
        "フォーマット":{"select": {"name" : str(log_entry.get("フォーマット", ""))}},
        "タイムスタンプ": {"date": {"start": log_entry.get("タイムスタンプ")}},
        "成否": {"checkbox": log_entry.get("成否", False)},
        "エラーメッセージ": {"rich_text": [{"text": {"content": log_entry.get("エラーメッセージ", "")}}]}
    }

    # 親ページが指定されている場合はリレーションを追加（プレイリスト用）
    if parent_page_id:
        properties["親アイテム"] = {"relation": [{"id": parent_page_id}]}

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties
    }

    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        response.raise_for_status() # エラーがあれば例外を発生させる
        page_id = response.json().get("id")
        print(f"ログをNotionにアップロードしました。 Page ID: {page_id}")
        return page_id
    except requests.exceptions.RequestException as e:
        print(f"Notionへのアップロードに失敗しました: {e}")
        if e.response:
            print(f"Response: {e.response.text}")
        return None

def write_log_to_file(log_entry):
    """ログエントリをローカルのJSONファイルに書き込む"""
    if not data.get('enable_logging', True):
        return

    log_file_path = data.get('log_file_path', file_path)
    
    # 既存のログを読み込む
    existing_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                existing_logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_logs = []
    
    # 新しいログを追加
    existing_logs.append(log_entry)
    
    # ログディレクトリが存在しない場合は作成
    log_dir = os.path.dirname(os.path.abspath(log_file_path))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに書き込む
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2, ensure_ascii=False)
        print(f"ログを書き込みました: {log_entry.get('ファイル名')}")
    except Exception as e:
        print(f"ログの書き込みに失敗しました: {e}")

def get_default_settings():
    """設定ファイルからデフォルトの保存先ディレクトリとフォーマットを取得する"""
    directories = data.get('directories', [])
    default_index = data.get('default_directory_index', 0)
    
    if not directories:
        print("ディレクトリが設定されていません。")
        return None, None
    
    # インデックスが範囲外の場合は最初のディレクトリを使用
    if default_index >= len(directories):
        default_index = 0
    
    default_dir_info = directories[default_index]
    return default_dir_info['path'], default_dir_info['format']

def get_download_options(dl_dir, format_choice):
    """yt-dlpのダウンロードオプションを生成する"""
    print("ダウンロードオプションを取得しています...")
    video_quality = data.get('video_quality', 'best')
    enable_volume_adjustment = data.get('enable_volume_adjustment', False)
    volume_level = data.get('volume_level', 1.0)
    use_cookies = data.get('use_cookies', False)
    cookie_browser = data.get('cookie_browser', 'chrome')

    options = {
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
        'postprocessors': [],
    }

    # Cookieを使用する場合の設定
    if use_cookies:
        options['cookies-from-browser'] = cookie_browser
        print(f"Cookieを使用します (ブラウザ: {cookie_browser})")

    print(f"画質: {video_quality}")
    if enable_volume_adjustment:
        print(f"音量調整: 有効 (レベル: {volume_level})")
    else:
        print("音量調整: 無効")

    # 画質指定がある場合のセレクタ
    quality_selector = ""
    if video_quality != 'best' and str(video_quality).isdigit():
        quality_selector = f"[height<=?{video_quality}]"

    # フォーマットに応じたオプション設定
    video_formats = ["mp4", "webm"]
    audio_formats = ["mp3", "wav", "flac"]

    if format_choice in video_formats:
        options['format'] = f'bestvideo{quality_selector}+bestaudio/best{quality_selector}/best'
        pp = {'key': 'FFmpegVideoConvertor', 'preferedformat': format_choice}
        if enable_volume_adjustment:
            pp['params'] = ['-af', f'volume={volume_level}']
        options['postprocessors'].append(pp)
    elif format_choice in audio_formats:
        options['format'] = 'bestaudio/best'
        pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': format_choice}
        if format_choice == 'mp3':
            pp['preferredquality'] = '192'
        if enable_volume_adjustment:
            pp['params'] = ['-af', f'volume={volume_level}']
        options['postprocessors'].append(pp)
    else:  # デフォルトは最高品質
        options['format'] = 'best'
        if enable_volume_adjustment:
            # FFmpegPostProcessor is more generic for unknown file types
            options['postprocessors'].append({
                'key': 'FFmpegPostProcessor',
                'params': ['-af', f'volume={volume_level}']
            })

    # If no postprocessors were added, remove the empty list
    if not options['postprocessors']:
        del options['postprocessors']

    return options

def get_video_urls(playlist_url):
    """再生リストのURLから個別の動画URLのリストを取得する"""
    print("再生リストの動画URLを取得しています...")
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, # 再生リストの情報をフラットに取得
        'skip_download': True # ダウンロードはしない
    }
    if data.get('use_cookies', False):
        ydl_opts['cookies-from-browser'] = data.get('cookie_browser', 'chrome')

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    
    if 'entries' in info:
        video_urls = [entry['url'] for entry in info['entries'] if 'url' in entry]
        return video_urls, info.get('title', '再生リスト')
    else:
        return [], '再生リスト'

def download_video(url, output_dir, format_choice):
    """指定されたURLの動画をダウンロードする"""
    print("ダウンロード開始")
    ydl_opts = get_download_options(output_dir, format_choice)
    if not ydl_opts:
        print("無効なフォーマットが選択されています。")
        return False, "無効なフォーマット", None

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False) # まず情報を取得
            title = info.get('title', 'Unknown Title')

            # ファイルが既に存在するかチェック
            temp_filepath = ydl.prepare_filename(info)
            base_filename = os.path.splitext(os.path.basename(temp_filepath))[0]
            final_filename = f"{base_filename}.{format_choice}"
            final_filepath = os.path.join(output_dir, final_filename)

            if os.path.exists(final_filepath):
                print(f"ファイルが既に存在するため、ダウンロードを中止します: {final_filepath}")
                return False, f"ファイルが既に存在: {final_filename}", title

            # ダウンロード実行
            ydl.download([url])
            print(f"✓ ダウンロード成功: {title}")
            return True, None, title
        except Exception as e:
            error_msg = str(e)
            # エラーメッセージからANSIエスケープシーケンスを削除
            clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            print(f"✗ エラーが発生しました: {clean_error_msg}")
            # エラーが発生してもタイトル取得を試みる
            try:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title')
            except:
                title = None
            return False, clean_error_msg, title

def main():
    """メイン処理"""
    # クリップボードからURLを取得
    video_url = pyperclip.paste()
    if not video_url or "https" not in video_url:
        print("クリップボードにURLがありません。")
        return

    print(f"処理対象URL: {video_url}")
    
    # デフォルト設定を取得
    output_dir, format_choice = get_default_settings()
    
    if not output_dir or not format_choice:
        print("設定が不正です。")
        return

    if not os.path.isdir(output_dir):
        print(f"保存先ディレクトリが存在しません: {output_dir}")
        return

    print(f"保存先: {output_dir}")
    print(f"形式: {format_choice}")

    if data.get('enable_logging', True):
        log_file = data.get('log_file_path', Path(__file__).parent / '設定・履歴/log.json')
        print(f"ログ機能: 有効 ({log_file})")
    else:
        print("ログ機能: 無効")

    # フォーマットに応じた品質情報を設定
    quality = 'best'
    if format_choice in ["mp4", "webm"]:
        quality = data.get('video_quality', 'best')
    elif format_choice == "mp3":
        quality = '192kbps'
    elif format_choice in ["wav", "flac"]:
        quality = 'lossless'

    # JSTタイムゾーンを設定
    jst = timezone(timedelta(hours=9), 'JST')

    # ダウンロード結果のカウンターを初期化
    total_downloads = 0
    successful_downloads = 0
    failed_downloads = 0
    error_messages = []
    filenames = []

    try:
        # yt-dlpでURLの情報を取得し、プレイリストかどうかを判定
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True
        }
        if data.get('use_cookies', False):
            ydl_opts['cookies-from-browser'] = data.get('cookie_browser', 'chrome')

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        is_playlist = 'entries' in info and info['entries']

        if is_playlist:
            # 再生リストの処理
            video_urls = [entry['url'] for entry in info['entries'] if 'url' in entry]
            playlist_title = info.get('title', '再生リスト')
            playlist_duration = 0

            if not video_urls:
                print("再生リストから動画URLを取得できませんでした。")
                error_messages.append("再生リストからURL取得失敗")
                failed_downloads = 1
                total_downloads = 1
            else:
                makedirector = data.get('makedirector', True)
                if makedirector:
                    safe_playlist_title = re.sub(r'[\\/*?:"<>|]', "_", playlist_title)
                    playlist_dir = os.path.join(output_dir, safe_playlist_title)
                    os.makedirs(playlist_dir, exist_ok=True)
                    final_output_dir = playlist_dir
                    print(f"再生リスト用ディレクトリを作成: {playlist_dir}")
                else:
                    final_output_dir = output_dir
                    print("再生リストの動画を直接指定ディレクトリに保存します。")

                total_downloads = len(video_urls)
                print(f"再生リスト内の動画数: {total_downloads}")
                
                video_logs = []
                for i, url in enumerate(video_urls, 1):
                    print(f"\nダウンロード中 ({i}/{total_downloads}): ")
                    success, error_msg, video_info = download_video(url, final_output_dir, format_choice)
                    
                    filename = video_info.get('title', 'タイトル取得失敗')
                    duration = video_info.get('duration')
                    if duration:
                        playlist_duration += duration

                    video_log = {
                        "タイムスタンプ": datetime.now(jst).isoformat(),
                        "URL": url,
                        "出力ディレクトリ": final_output_dir,
                        "形式": format_choice,
                        "フォーマット": quality,
                        "ファイル名": filename,
                        "時間": duration,
                        "成否": success,
                        "エラーメッセージ": "" if success else error_msg
                    }
                    video_logs.append(video_log)

                    if success:
                        successful_downloads += 1
                        filenames.append(filename)
                    else:
                        failed_downloads += 1
                        if error_msg:
                            error_messages.append(error_msg)
                        filenames.append(filename)
                
                is_playlist_success = failed_downloads == 0
                playlist_log = {
                    "タイムスタンプ": datetime.now(jst).isoformat(),
                    "URL": video_url,
                    "出力ディレクトリ": final_output_dir,
                    "形式": format_choice,
                    "フォーマット": quality,
                    "ファイル名": f"{playlist_title} ({total_downloads}件)",
                    "時間": playlist_duration,
                    "成否": is_playlist_success,
                    "エラーメッセージ": "" if is_playlist_success else '; '.join(error_messages)
                }

                write_log_to_file(playlist_log)

                if data.get('enable_notion_upload', False):
                    print("\nNotionへのアップロードを開始します...")
                    parent_page_id = upload_to_notion(playlist_log)
                    if parent_page_id:
                        print(f"プレイリストの親ページをNotionに作成しました。ID: {parent_page_id}")
                        print("各動画のログをサブアイテムとして登録します。")
                        for v_log in video_logs:
                            upload_to_notion(v_log, parent_page_id=parent_page_id)
                            write_log_to_file(v_log)
                    else:
                        print("親ページの作成に失敗したため、サブアイテムの登録をスキップします。")
                        for v_log in video_logs:
                            write_log_to_file(v_log)
                else:
                    for v_log in video_logs:
                        write_log_to_file(v_log)

        else: # 単体動画のダウンロード
            print("個別動画をダウンロードしています...")
            total_downloads = 1
            success, error_msg, video_info = download_video(video_url, output_dir, format_choice)
            
            filename = video_info.get('title') if video_info else None
            duration = video_info.get('duration') if video_info else None

            if success:
                successful_downloads = 1
                if filename:
                    filenames.append(filename)
            else:
                failed_downloads = 1
                if error_msg:
                    error_messages.append(error_msg)
                if filename:
                    filenames.append(filename)

            initialize_session(video_url, output_dir, format_choice, quality)
            session_info['時間'] = duration
            update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages, filenames)
            
            write_log_to_file(session_info)
            upload_to_notion(session_info)

    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        error_log = {
            "タイムスタンプ": datetime.now(jst).isoformat(),
            "URL": video_url,
            "成否": False,
            "エラーメッセージ": f"予期しないエラー: {str(e)}"
        }
        write_log_to_file(error_log)

    finally:
        print(f"\n{'='*50}")
        print("ダウンロード完了！")
        print(f"総数: {total_downloads}, 成功: {successful_downloads}, 失敗: {failed_downloads}")
        
        if failed_downloads > 0:
            print(f"⚠️ {failed_downloads}件のダウンロードに失敗しました。")
        else:
            print("✓ すべてのダウンロードが完了しました。")
        print(f"{'='*50}")

# ffmpegのパスを設定（環境変数PATHに追加）
ffmpeg_path = data.get('ffmpeg_path', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe')
if ffmpeg_path and os.path.exists(ffmpeg_path):
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] += os.pathsep + ffmpeg_dir

if __name__ == "__main__":
    main()