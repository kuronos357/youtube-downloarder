import os
import json
import re
import pyperclip
import requests # Notion APIのために追加
from yt_dlp import YoutubeDL
from datetime import datetime

file_path = "/home/kuronos357/programming/Project/youtube-downloarder/設定・履歴/config.json"  # 設定ファイルのパス

# jsonファイルを読み込む関数
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

data = read_json(file_path)

# セッション情報を保持するグローバル変数
session_info = {}

def initialize_session(url, output_dir, format_choice, quality):
    print("セッション開始時に情報を初期化")
    global session_info
    session_info = {
        "タイムスタンプ": datetime.now().isoformat(),
        "URL": url,
        "出力ディレクトリ": output_dir,
        "形式": format_choice,
        "フォーマット": quality, # ステータスを品質情報に置き換え
        "ファイル名": "",
        "成否とエラーメッセージ": ""
    }

def update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages=None, filenames=None):
    print("セッション終了時に結果を更新")
    global session_info
    
    # ファイル名を設定
    if filenames and len(filenames) > 0:
        if len(filenames) == 1:
            session_info["ファイル名"] = filenames[0]
        else:
            session_info["ファイル名"] = f"{filenames[0]} 他{len(filenames)-1}件"
    elif failed_downloads > 0:
        # 失敗時にファイル名が取得できなかった場合、URLをファイル名として使用
        session_info["ファイル名"] = session_info.get("URL", "タイトル取得失敗")

    # 成否とエラーメッセージを設定
    summary = f"Total: {total_downloads}, Success: {successful_downloads}, Failed: {failed_downloads}"
    if failed_downloads > 0 and error_messages:
        # エラーがある場合はエラーメッセージも含める
        session_info["成否とエラーメッセージ"] = f"{summary}, Errors: {'; '.join(error_messages[:3])}"  # 最初の3つのエラーのみ
    else:
        session_info["成否とエラーメッセージ"] = summary

def upload_to_notion(log_entry):
    print("ログエントリをNotionデータベースにアップロード...")

    if not data.get('enable_notion_upload', False):
        return

    api_key = data.get('notion_api_key')
    database_id = data.get('notion_database_id')

    if not api_key or not database_id:
        print("NotionのAPIキーまたはデータベースIDがconfig.jsonに設定されていません。")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Notionのプロパティ名とログのキーをマッピング
    properties = {
        "ファイル名": {"title": [{"text": {"content": log_entry.get("ファイル名", "N/A")}}]},
        "URL": {"url": log_entry.get("URL")},
        "出力ディレクトリ": {"rich_text": [{"text": {"content": log_entry.get("出力ディレクトリ", "")}}]},
        "形式": {"rich_text": [{"text": {"content": log_entry.get("形式", "")}}]},
        "フォーマット": {"rich_text": [{"text": {"content": str(log_entry.get("フォーマット", ""))}}]},
        "成否とエラーメッセージ": {"rich_text": [{"text": {"content": log_entry.get("成否とエラーメッセージ", "")}}]},
        "タイムスタンプ": {"date": {"start": log_entry.get("タイムスタンプ")}} 
    }

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties
    }

    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        response.raise_for_status()
        print("ログをNotionにアップロードしました。")
    except requests.exceptions.RequestException as e:
        print(f"Notionへのアップロードに失敗しました: {e}")
        if e.response:
            print(f"Response: {e.response.text}")

def write_session_log():
    print("セッション終了時に1つのログエントリを書き込み、Notionにアップロード")
    if not session_info:
        return

    # ローカルファイルへのログ書き込み
    if data.get('enable_logging', True):
        log_file_path = data.get('log_file_path', file_path)
        
        existing_logs = []
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_logs = []
        
        existing_logs.append(session_info)
        
        log_dir = os.path.dirname(os.path.abspath(log_file_path))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)
            print(f"ログを書き込みました: 1件のエントリ")
        except Exception as e:
            print(f"ログの書き込みに失敗しました: {e}")

    # Notionへのアップロード
    upload_to_notion(session_info)


# デフォルトディレクトリとフォーマットを取得する関数
def get_default_settings():
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

# 対話的にディレクトリを選択する関数
def select_directory_interactive():
    directories = data.get('directories', [])
    if not directories:
        print("ディレクトリが設定されていません。")
        return None, None
    
    if len(directories) == 1:
        # ディレクトリが1つしかない場合はそれを使用
        return directories[0]['path'], directories[0]['format']
    
    print("\n利用可能なディレクトリ:")
    for i, dir_info in enumerate(directories):
        print(f"{i + 1}. {dir_info['path']} (形式: {dir_info['format']})")
    
    while True:
        try:
            choice = input(f"\nディレクトリを選択してください (1-{len(directories)}): ").strip()
            if not choice:
                # 空入力の場合はデフォルトを使用
                return get_default_settings()
            
            index = int(choice) - 1
            if 0 <= index < len(directories):
                selected = directories[index]
                return selected['path'], selected['format']
            else:
                print(f"1から{len(directories)}の間で選択してください。")
        except ValueError:
            print("数字を入力してください。")

# ダウンロードオプションを取得する関数
def get_download_options(dl_dir, format_choice):
    print("ダウンロードオプションを取得しています...")
    download_subtitles = data.get('download_subtitles', False)
    embed_subtitles = data.get('embed_subtitles', False)
    video_quality = data.get('video_quality', 'best')
    enable_volume_adjustment = data.get('enable_volume_adjustment', False)
    volume_level = data.get('volume_level', 1.0)
    use_cookies = data.get('use_cookies', False)
    cookie_browser = data.get('cookie_browser', 'chrome')
    
    options = {
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
    }

    if use_cookies:
        options['cookies-from-browser'] = cookie_browser
        print(f"Cookieを使用します (ブラウザ: {cookie_browser})")

    print(f"画質: {video_quality}")
    if enable_volume_adjustment:
        print(f"音量調整: 有効 (レベル: {volume_level})")
    else:
        print("音量調整: 無効")

    quality_selector = ""
    if video_quality != 'best' and str(video_quality).isdigit():
        quality_selector = f"[height<=?{video_quality}]"

    if format_choice == "mp4":
        options['format'] = f'bestvideo{quality_selector}[ext=mp4]+bestaudio[ext=m4a]/best{quality_selector}[ext=mp4]/best'
        if enable_volume_adjustment:
            options['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
                'params': ['-af', f'volume={volume_level}']
            }]
    elif format_choice == "mp3":
        options['format'] = 'bestaudio'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        if enable_volume_adjustment:
            postprocessors[0]['params'] = ['-af', f'volume={volume_level}']
        options['postprocessors'] = postprocessors
    elif format_choice == "webm":
        options['format'] = f'bestvideo{quality_selector}[ext=webm]+bestaudio[ext=webm]/best{quality_selector}[ext=webm]/best'
        if enable_volume_adjustment:
            options['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'webm',
                'params': ['-af', f'volume={volume_level}']
            }]
    elif format_choice == "wav":
        options['format'] = 'bestaudio'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }]
        if enable_volume_adjustment:
            postprocessors[0]['params'] = ['-af', f'volume={volume_level}']
        options['postprocessors'] = postprocessors
    elif format_choice == "flac":
        options['format'] = 'bestaudio'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
        }]
        if enable_volume_adjustment:
            postprocessors[0]['params'] = ['-af', f'volume={volume_level}']
        options['postprocessors'] = postprocessors
    else:
        options['format'] = 'best'
        if enable_volume_adjustment:
            options['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'params': ['-af', f'volume={volume_level}']
            }]

    if download_subtitles:
        options['subtitleslangs'] = ['all']
        options['writesubtitles'] = True
        print("字幕をダウンロードします。")

    if embed_subtitles:
        options['postprocessors'] = options.get('postprocessors', [])
        options['postprocessors'].append({
            'key': 'FFmpegEmbedSubtitle',
        })
        print("字幕を埋め込みます。")

    return options

# 再生リストのURLから個別の動画URLを取得する関数
def get_video_urls(playlist_url):
    print("再生リストの動画URLを取得しています...")
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
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

# ダウンロード処理を行う関数
def download_video(url, output_dir, format_choice):
    ydl_opts = get_download_options(output_dir, format_choice)
    if not ydl_opts:
        print("無効なフォーマットが選択されています。")
        return False, "無効なフォーマット", None

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            ydl.download([url])
            print(f"✓ ダウンロード成功: {title}")
            return True, None, title
        except Exception as e:
            error_msg = str(e)
            clean_error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            print(f"✗ エラーが発生しました: {clean_error_msg}")
            # タイトル取得を試みる
            try:
                info = ydl.extract_info(url, download=False) # download=Falseで再試行
                title = info.get('title', 'Unknown Title')
            except:
                title = None
            return False, clean_error_msg, title

# メイン処理
def main():
    video_url = pyperclip.paste()
    if not video_url or "https" not in video_url:
        print("クリップボードにURLがありません。")
        return

    print(f"処理対象URL: {video_url}")
    
    interactive_selection = data.get('interactive_selection', False)
    
    if interactive_selection:
        output_dir, format_choice = select_directory_interactive()
    else:
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
        log_file = data.get('log_file_path', 'python/youtube-downloarder/download_log.json')
        print(f"ログ機能: 有効 ({log_file})")
    else:
        print("ログ機能: 無効")

    quality = 'best'
    if format_choice in ["mp4", "webm"]:
        quality = data.get('video_quality', 'best')
    elif format_choice == "mp3":
        quality = '192kbps'
    elif format_choice in ["wav", "flac"]:
        quality = 'lossless'

    initialize_session(video_url, output_dir, format_choice, quality)

    total_downloads = 0
    successful_downloads = 0
    failed_downloads = 0
    error_messages = []
    filenames = []

    try:
        is_playlist = "playlist" in video_url
        if is_playlist:
            video_urls, playlist_title = get_video_urls(video_url)
            if not video_urls:
                print("再生リストから動画URLを取得できませんでした。")
                error_messages.append("再生リストからURL取得失敗")
                failed_downloads = 1
                total_downloads = 1
            else:
                makedirector = data.get('makedirector', True)
                if makedirector:
                    playlist_dir = os.path.join(output_dir, playlist_title)
                    os.makedirs(playlist_dir, exist_ok=True)
                    final_output_dir = playlist_dir
                    print(f"再生リスト用ディレクトリを作成: {playlist_dir}")
                else:
                    final_output_dir = output_dir
                    print("再生リストの動画を直接指定ディレクトリに保存します。")

                total_downloads = len(video_urls)
                print(f"再生リスト内の動画数: {total_downloads}")
                
                for i, url in enumerate(video_urls, 1):
                    print(f"\nダウンロード中 ({i}/{total_downloads}): ")
                    success, error_msg, filename = download_video(url, final_output_dir, format_choice)
                    if success:
                        successful_downloads += 1
                        if filename:
                            filenames.append(filename)
                    else:
                        failed_downloads += 1
                        if error_msg:
                            error_messages.append(error_msg)
                        if filename: # エラーでもタイトルが取れた場合
                            filenames.append(filename)
        else:
            print("個別動画をダウンロードしています...")
            total_downloads = 1
            success, error_msg, filename = download_video(video_url, output_dir, format_choice)
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

    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        error_messages.append(f"予期しないエラー: {str(e)}")
        failed_downloads = total_downloads if total_downloads > 0 else 1
        total_downloads = total_downloads if total_downloads > 0 else 1

    finally:
        update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages, filenames)
        write_session_log()

        print(f"\n{'='*50}")
        print("ダウンロード完了！")
        print(f"総数: {total_downloads}, 成功: {successful_downloads}, 失敗: {failed_downloads}")
        
        if failed_downloads > 0:
            print(f"⚠️ {failed_downloads}件のダウンロードに失敗しました。")
            if data.get('enable_logging', True):
                print("詳細はログファイルを確認してください。")
        else:
            print("✓ すべてのダウンロードが完了しました。")
        print(f"{'='*50}")

ffmpeg_path = data.get('ffmpeg_path', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe')
if ffmpeg_path and os.path.exists(ffmpeg_path):
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] += os.pathsep + ffmpeg_dir

if __name__ == "__main__":
    main()