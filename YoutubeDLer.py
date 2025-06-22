import os
import json
import pyperclip
from yt_dlp import YoutubeDL

file_path = "python/youtube-downloarder/設定json/config.json"  # 設定ファイルのパス

# jsonファイルを読み込む関数
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

data = read_json(file_path)

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
        return

    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            print(f"エラーが発生しました: {e}")

# メイン処理
def main():
    video_url = pyperclip.paste()
    if not video_url or "https" not in video_url:
        print("クリップボードにURLがありません。")
        return

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

    # 再生リストの場合、個別の動画URLを取得
    if "playlist" in video_url:
        video_urls, playlist_title = get_video_urls(video_url)
        if not video_urls:
            print("再生リストから動画URLを取得できませんでした。")
            return

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

        print(f"再生リスト内の動画数: {len(video_urls)}")
        for i, url in enumerate(video_urls, 1):
            print(f"ダウンロード中 ({i}/{len(video_urls)}): {url}")
            download_video(url, final_output_dir, format_choice)
    else:
        # 個別の動画URLの場合
        print("個別動画をダウンロードしています...")
        download_video(video_url, output_dir, format_choice)

    print("ダウンロード完了！")

# ffmpegのパスを設定
ffmpeg_path = data.get('ffmpeg_path', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe')
if ffmpeg_path and os.path.exists(ffmpeg_path):
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] += os.pathsep + ffmpeg_dir

if __name__ == "__main__":
    main()