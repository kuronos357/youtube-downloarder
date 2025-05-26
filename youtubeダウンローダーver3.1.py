import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from yt_dlp import YoutubeDL
import os


# ダウンロードオプションを取得するための関数
def get_download_options(dl_dir):
    print("test")
    print(str(dl_dir)+"dl_dir")
    return {
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),  # 保存先ディレクトリを指定
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
    

path = 'C:\ProgramData\chocolatey\bin\ffmpeg.exe' #ffmegのパス指定
os.environ['PATH'] +=  '' if path in os.environ['PATH'] else ';' + path 

# GUIの設定
root = tk.Tk()
root.withdraw()  # メインウィンドウを隠す

# URL入力ダイアログ
url = simpledialog.askstring("Input", "Enter the YouTube video URL:")
if not url:
    messagebox.showerror("Error", "URLを入力していません")


 # 保存先のディレクトリ選択ダイアログ
output_dir = filedialog.askdirectory(title="Select the directory to save the file")
if not output_dir:
    messagebox.showerror("Error", "ディレクトリを選択していません")

os.startfile(output_dir)#選択したディレクトリを開く
print(str(output_dir))

# ダウンロード処理
download_video(url, output_dir)