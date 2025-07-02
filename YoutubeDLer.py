import os
import json
import pyperclip
from yt_dlp import YoutubeDL
from datetime import datetime

file_path = "python/youtube-downloarder/設定json/config.json"  # 設定ファイルのパス

# jsonファイルを読み込む関数
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

data = read_json(file_path)

# セッション情報を保持するグローバル変数
session_info = {}

def initialize_session(url, output_dir, format_choice):
    """セッション開始時に情報を初期化"""
    global session_info
    session_info = {
        "タイムスタンプ": datetime.now().isoformat(),
        "URL": url,
        "出力ディレクトリ": output_dir,
        "形式": format_choice,
        "ステータス": "success",  # デフォルトは成功、エラーがあれば後で変更
        "ファイル名": "",
        "成否とエラーメッセージ": ""
    }

def update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages=None, filenames=None):
    """セッション終了時に結果を更新"""
    global session_info
    
    # ステータスを決定
    if failed_downloads > 0:
        session_info["ステータス"] = "error"
    else:
        session_info["ステータス"] = "success"
    
    # ファイル名を設定（複数の場合は最初のもの、または代表的なもの）
    if filenames and len(filenames) > 0:
        if len(filenames) == 1:
            session_info["ファイル名"] = filenames[0]
        else:
            session_info["ファイル名"] = f"{filenames[0]} 他{len(filenames)-1}件"
    
    # 成否とエラーメッセージを設定
    summary = f"Total: {total_downloads}, Success: {successful_downloads}, Failed: {failed_downloads}"
    if failed_downloads > 0 and error_messages:
        # エラーがある場合はエラーメッセージも含める
        session_info["成否とエラーメッセージ"] = f"{summary}, Errors: {'; '.join(error_messages[:3])}"  # 最初の3つのエラーのみ
    else:
        session_info["成否とエラーメッセージ"] = summary

def write_session_log():
    """セッション終了時に1つのログエントリを書き込み"""
    if not data.get('enable_logging', True) or not session_info:
        return
    
    log_file_path = data.get('log_file_path', 'python/youtube-downloarder/download_log.json')
    
    # 既存のログを読み込み
    existing_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                existing_logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_logs = []
    
    # 新しいセッションログを既存ログに追加
    existing_logs.append(session_info)
    
    # ログファイルのディレクトリが存在しない場合は作成
    log_dir = os.path.dirname(os.path.abspath(log_file_path))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに書き込み
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2, ensure_ascii=False)
        print(f"ログを書き込みました: 1件のエントリ")
    except Exception as e:
        print(f"ログの書き込みに失敗しました: {e}")

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
    download_subtitles = data.get('download_subtitles', False)  # 字幕ダウンロード設定を取得
    embed_subtitles = data.get('embed_subtitles', False)  # 字幕埋め込み設定を取得
    
    options = {
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
    }

    if format_choice == "mp4":  # mp4
        options['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    elif format_choice == "mp3":  # mp3
        options['format'] = 'bestaudio'
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_choice == "webm":  # webm
        options['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'
    elif format_choice == "wav":  # wav
        options['format'] = 'bestaudio'
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }]
    elif format_choice == "flac":  # flac
        options['format'] = 'bestaudio'
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
        }]
    else:
        options['format'] = 'best'

    # 字幕ダウンロードの設定を追加
    if download_subtitles:
        options['subtitleslangs'] = ['all']  # すべての言語の字幕をダウンロード
        options['writesubtitles'] = True    # 字幕ファイルをダウンロード
        print("字幕をダウンロードします。")

    # 字幕埋め込みの設定を追加
    if embed_subtitles:
        options['postprocessors'] = options.get('postprocessors', [])
        options['postprocessors'].append({
            'key': 'FFmpegEmbedSubtitle',  # 字幕を埋め込む
        })
        print("字幕を埋め込みます。")

    return options

# 再生リストのURLから個別の動画URLを取得する関数
def get_video_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # 動画情報のみ取得
        'skip_download': True
    }
    
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
            # ダウンロード前に動画情報を取得してタイトルを取得
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            
            # ダウンロード実行
            ydl.download([url])
            
            print(f"✓ ダウンロード成功: {title}")
            return True, None, title
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ エラーが発生しました: {error_msg}")
            return False, error_msg, None

# メイン処理
def main():
    video_url = pyperclip.paste()
    if not video_url or "https" not in video_url:
        print("クリップボードにURLがありません。")
        return

    print(f"処理対象URL: {video_url}")
    
    # 対話的選択の設定を確認
    interactive_selection = data.get('interactive_selection', False)
    
    if interactive_selection:
        # 対話的にディレクトリを選択
        output_dir, format_choice = select_directory_interactive()
    else:
        # デフォルト設定を使用
        output_dir, format_choice = get_default_settings()
    
    if not output_dir or not format_choice:
        print("設定が不正です。")
        return

    if not os.path.isdir(output_dir):
        print(f"保存先ディレクトリが存在しません: {output_dir}")
        return

    print(f"保存先: {output_dir}")
    print(f"形式: {format_choice}")

    # ログ機能の状態を表示
    if data.get('enable_logging', True):
        log_file = data.get('log_file_path', 'python/youtube-downloarder/download_log.json')
        print(f"ログ機能: 有効 ({log_file})")
    else:
        print("ログ機能: 無効")

    # セッション情報を初期化
    initialize_session(video_url, output_dir, format_choice)

    # 統計用変数
    total_downloads = 0
    successful_downloads = 0
    failed_downloads = 0
    error_messages = []
    filenames = []

    try:
        # 再生リストの場合、個別の動画URLを取得
        is_playlist = "playlist" in video_url
        if is_playlist:
            video_urls, playlist_title = get_video_urls(video_url)
            if not video_urls:
                print("再生リストから動画URLを取得できませんでした。")
                error_messages.append("再生リストからURL取得失敗")
                failed_downloads = 1
                total_downloads = 1
            else:
                # makedirectorの設定を確認してディレクトリ作成を決定
                makedirector = data.get('makedirector', True)
                if makedirector:
                    # 再生リスト用のディレクトリを作成
                    playlist_dir = os.path.join(output_dir, playlist_title)
                    os.makedirs(playlist_dir, exist_ok=True)
                    final_output_dir = playlist_dir
                    print(f"再生リスト用ディレクトリを作成: {playlist_dir}")
                else:
                    # 直接指定されたディレクトリに保存
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
        else:
            # 個別の動画URLの場合
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

    except Exception as e:
        # 予期しないエラーの場合
        print(f"予期しないエラーが発生しました: {e}")
        error_messages.append(f"予期しないエラー: {str(e)}")
        failed_downloads = total_downloads if total_downloads > 0 else 1
        total_downloads = total_downloads if total_downloads > 0 else 1

    finally:
        # セッション結果を更新
        update_session_result(total_downloads, successful_downloads, failed_downloads, error_messages, filenames)
        
        # ログを書き込み
        write_session_log()

        # 結果サマリーを表示
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

# ffmpegのパスを設定
ffmpeg_path = data.get('ffmpeg_path', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe')
if ffmpeg_path and os.path.exists(ffmpeg_path):
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] += os.pathsep + ffmpeg_dir

if __name__ == "__main__":
    main()