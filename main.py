import tkinter as tk
from yt_dlp import YoutubeDL
import os
from tkinter import filedialog, messagebox, Label, Button, Entry

# ダウンロードオプションを取得する関数
def get_download_options(dl_dir, format_choice):
    if format_choice == "1":  # mp4
        return {
            'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
        } 
    elif format_choice == "2":  # mp3
        return {
            'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        return {
            'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
        }
        

# ダウンロード処理を行う関数
def download_video(url, output_dir, format_choice):
    ydl_opts = get_download_options(output_dir, format_choice)
    if not ydl_opts:
        messagebox.showerror("Error", "無効なフォーマットが選択されています。")
        return

    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])

            selected_dir = output_dir_label.cget("text")
            if os.path.isdir(selected_dir):
                os.startfile(selected_dir)
        except Exception as e:
            messagebox.showerror("Error", f"エラーが発生しました: {e}")

# 保存先ディレクトリを選択する関数
def select_output_directory():
    selected_dir = filedialog.askdirectory(title="保存先のディレクトリを選択してください")
    if selected_dir:
        output_dir_label.config(text=selected_dir)
    return selected_dir

# エクスプローラーでディレクトリを開く関数
def open_selected_directory():
    Label(root, text="ダウンロード完了").pack(pady=5)
    selected_dir = output_dir_label.cget("text")
    if os.path.isdir(selected_dir):
        print("snkeiao")
    else:
        messagebox.showerror("Error", "有効なディレクトリが選択されていません。")

# ダウンロードを開始する関数
def start_download():
    video_url = url_entry.get()
    output_dir = output_dir_label.cget("text")
    format_choice = selected_option.get()

    if not video_url:
        messagebox.showerror("Error", "URLが入力されていません。")
        return

    if not os.path.isdir(output_dir):
        messagebox.showerror("Error", "有効な保存先ディレクトリが選択されていません。")
        return

    download_video(video_url, output_dir, format_choice)

# ffmpegのパスを設定
ffmpeg_path = r'C:\ProgramData\chocolatey\bin\ffmpeg.exe'
if ffmpeg_path not in os.environ['PATH']:
    os.environ['PATH'] += ';' + ffmpeg_path

# GUIの設定
root = tk.Tk()
root.title("YouTubeダウンローダー")
root.geometry("400x400")

# URL入力フィールド
Label(root, text="YouTube動画のURLを入力してください:").pack(pady=5)
url_entry = Entry(root, width=50)
url_entry.pack(pady=5)

# 保存先ディレクトリ選択ボタン
Button(root, text="保存先のディレクトリを選択", command=select_output_directory).pack(pady=5)
output_dir_label = Label(root, text="保存先ディレクトリが選択されていません")
output_dir_label.pack(pady=5)

# フォーマット選択ラジオボタン
selected_option = tk.StringVar(value="3")  # 初期値は無選択
Label(root, text="フォーマットを選択してください:").pack(pady=5)
tk.Radiobutton(root, text="動画", variable=selected_option, value="1").pack()
tk.Radiobutton(root, text="mp3", variable=selected_option, value="2").pack()
tk.Radiobutton(root, text="無選択", variable=selected_option, value="3").pack()

# ダウンロード開始ボタン
Button(root, text="ダウンロード開始", command=start_download).pack(pady=5)

# エクスプローラーでディレクトリを開くボタン
#Button(root, text="保存先ディレクトリを開く", command=open_selected_directory).pack(pady=5)

# メインループの開始
root.mainloop()
