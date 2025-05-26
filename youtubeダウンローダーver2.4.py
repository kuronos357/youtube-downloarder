import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from yt_dlp import YoutubeDL
import os

path = 'C:\ProgramData\chocolatey\bin\ffmpeg.exe' 
os.environ['PATH'] +=  '' if path in os.environ['PATH'] else ';' + path
# ダウンロードオプションを取得するための関数
def get_download_options(dl_dir):
    return {
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),  # 保存先ディレクトリを指定
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  
            'preferredcodec': 'mp3',  #変換したい形式を指定
            'preferredquality': '192' #ビットレートを指定
        }]
    }

# ダウンロード処理を行う関数
def download_video(url, output_dir):
    ydl_opts = get_download_options(output_dir)
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            
            
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


# エクスプローラーでディレクトリを開く関数
def open_directory(path):
    if os.name == 'nt':  # Windowsの場合
        os.startfile(path)

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
print(str(output_dir)+"outoput_dir")




# ダウンロード処理
download_video(url, output_dir)
open_directory(output_dir)