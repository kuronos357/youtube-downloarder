import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from yt_dlp import YoutubeDL
import os
import subprocess

# ダウンロードオプションを取得するための関数
def get_download_options(dl_dir):
    print("test")
    print(str(dl_dir)+"dl_dir")


    return {

        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),  # 保存先ディレクトリを指定
        'ffmpeg_location': 'C:\ProgramData\chocolatey\bin\ffmpeg.exe', # ffmpegのパスを指定
        'format' : 'bestvideo+bestaudio/best'
    }

# ダウンロード処理を行う関数
def download_video(url, output_dir):
    ydl_opts = get_download_options(output_dir)
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            
            
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


# GUIの設定
root = tk.Tk()
root.withdraw()  # メインウィンドウを隠す

# URL入力ダイアログ
url = simpledialog.askstring("Input", "Enter the YouTube video URL:")
if not url:
    messagebox.showerror("Error", "No URL provided")

 # 保存先のディレクトリ選択ダイアログ
output_dir = filedialog.askdirectory(title="Select the directory to save the file")
print("test")
os.startfile(output_dir)

print(str(output_dir)+"outoput_dir")

if not output_dir:
    messagebox.showerror("Error", "No directory selected")

# ダウンロード処理
download_video(url, output_dir)