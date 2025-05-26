import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from yt_dlp import YoutubeDL
import os
import subprocess

# ダウンロードオプションを取得するための関数
def get_download_options(output_dir):
    return {
        'format':'best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  # 保存先ディレクトリを指定
        'ffmpeg_location': r'C:\ffmpeg\bin',  # ffmpegのパスを指定
    }

# ダウンロード処理を行う関数
def download_video(url, output_dir):
    ydl_opts = get_download_options(output_dir)
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            # ダウンロード後にエクスプローラーでディレクトリを開く
            open_directory(output_dir)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

# エクスプローラーでディレクトリを開く関数
def open_directory(path):
    if os.name == 'nt':  # Windowsの場合
        subprocess.run(['explorer', path])
    else:
        messagebox.showinfo("Info", "This function is only supported on Windows.")

# GUIの設定
def run_downloader():
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを隠す

    # URL入力ダイアログ
    url = simpledialog.askstring("Input", "Enter the YouTube video URL:")
    if not url:
        messagebox.showerror("Error", "No URL provided")
        return

    # 保存先のディレクトリ選択ダイアログ
    output_dir = filedialog.askdirectory(title="Select the directory to save the file")
    if not output_dir:
        messagebox.showerror("Error", "No directory selected")
        return

    # ダウンロード処理
    download_video(url, output_dir)

# メイン処理
if __name__ == "__main__":
    run_downloader()
