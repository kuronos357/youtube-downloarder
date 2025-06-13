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

    output_dir = data.get('default_directory', "保存先ディレクトリが選択されていません")
    format_choice = data.get('default_format', "3")

    if not os.path.isdir(output_dir):
        print("有効な保存先ディレクトリが選択されていません。")
        return

    # 再生リストの場合、個別の動画URLを取得
    if "playlist" in video_url:
        video_urls, playlist_title = get_video_urls(video_url)
        if not video_urls:
            print("再生リストから動画URLを取得できませんでした。")
            return

        # 再生リスト用のディレクトリを作成
        playlist_dir = os.path.join(output_dir, playlist_title)
        os.makedirs(playlist_dir, exist_ok=True)

        print(f"再生リスト内の動画数: {len(video_urls)}")
        for url in video_urls:
            download_video(url, playlist_dir, format_choice)
    else:
        # 個別の動画URLの場合
        download_video(video_url, output_dir, format_choice)

# ffmpegのパスを設定
ffmpeg_path = data.get('ffmpeg_path', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe')
if ffmpeg_path not in os.environ['PATH']:
    os.environ['PATH'] += ';' + ffmpeg_path

if __name__ == "__main__":
    main()
