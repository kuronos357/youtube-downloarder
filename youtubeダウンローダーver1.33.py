import tkinter as tk
from tkinter import simpledialog
from yt_dlp import YoutubeDL
import os
import subprocess

# ダウンロードオプションを設定
output_dir = r'D:\ピクチャ\youtube\素材\a共通\BGM'

# URLを入力するダイアログを表示
url = simpledialog.askstring("youtube音声用ダウンローダー", "ここにyoutubeのURLを入力:")


ydl_opts = {
    'format': 'bestaudio[ext=webm]',  # WebM形式の音声を選択
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  # 保存先ディレクトリを指定
}

def download_video(url):
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            # ダウンロード後にエクスプローラーでディレクトリを開く
            open_directory(output_dir)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

def open_directory(path):
    # エクスプローラーでディレクトリを開く
    if os.name == 'nt':  # Windowsの場合
        subprocess.run(['explorer', path])
    else:
        print(f"Directory opening is not supported on this OS.")

# Tkinterのウィンドウを作成
root = tk.Tk()
root.withdraw()  # メインウィンドウを隠す

# URLを入力するダイアログを表示


# URLが入力された場合にダウンロードを開始
if url:
    download_video(url)
else:
    print("No URL provided")
