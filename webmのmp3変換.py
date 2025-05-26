import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess

def convert_webm_to_mp3(input_file, output_dir):
    # 入力ファイル名からMP3の出力パスを作成
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}.mp3")
    
    # ffmpegコマンドを実行して変換
    try:
        subprocess.run(['ffmpeg', '-i', input_file, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', output_file], check=True)
        messagebox.showinfo("Success", f"Conversion complete: {output_file}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred during conversion: {e}")
    except FileNotFoundError:
        messagebox.showerror("Error", "ffmpeg not found. Please ensure ffmpeg is installed and added to PATH.")

def run_converter():
    # Tkinterウィンドウの設定
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを隠す

    # webmファイルの選択ダイアログ
    input_file = filedialog.askopenfilename(title="Select the .webm file", filetypes=[("WEBM files", "*.webm")])
    if not input_file:
        messagebox.showerror("Error", "No .webm file selected")
        return

    # 出力ディレクトリの選択ダイアログ
    output_dir = filedialog.askdirectory(title="Select the directory to save the MP3 file")
    if not output_dir:
        messagebox.showerror("Error", "No directory selected")
        return

    # 変換処理
    convert_webm_to_mp3(input_file, output_dir)

# メイン処理
if __name__ == "__main__":
    run_converter()
