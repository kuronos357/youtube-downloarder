import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import subprocess

def convert_file(input_file, output_dir, output_format):
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}.{output_format}")

    # 音声フォーマットと動画フォーマットの定義
    audio_formats = {
        'mp3': ['-vn', '-acodec', 'libmp3lame', '-q:a', '2'],
        'wav': ['-vn', '-acodec', 'pcm_s16le'],
        'aac': ['-vn', '-acodec', 'aac', '-b:a', '192k'],
        'ogg': ['-vn', '-acodec', 'libvorbis', '-q:a', '4'],
        'flac': ['-vn', '-acodec', 'flac']
    }
    video_formats = {
        'mp4': ['-c:v', 'libx264', '-c:a', 'aac', '-strict', 'experimental'],
        'mkv': ['-c', 'copy'], # 高速（再エンコードなし）
        'mov': ['-c:v', 'libx264', '-c:a', 'aac'],
        'avi': ['-c:v', 'mpeg4', '-c:a', 'mp3']
    }

    command = ['ffmpeg', '-i', input_file]
    
    if output_format in audio_formats:
        command.extend(audio_formats[output_format])
    elif output_format in video_formats:
        command.extend(video_formats[output_format])
    else:
        supported = ', '.join(list(audio_formats.keys()) + list(video_formats.keys()))
        messagebox.showerror("エラー", f"サポートされていない出力フォーマットです: {output_format}\n対応フォーマット: {supported}")
        return

    command.append(output_file)

    try:
        subprocess.run(command, check=True)
        messagebox.showinfo("成功", f"変換が完了しました: {output_file}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("エラー", f"変換中にエラーが発生しました: {e}")
    except FileNotFoundError:
        messagebox.showerror("エラー", "ffmpegが見つかりません。ffmpegがインストールされ、PATHに追加されていることを確認してください。")

def run_converter():
    root = tk.Tk()
    root.withdraw()

    filetypes = [
        ("メディアファイル", "*.mp4 *.mkv *.webm *.flv *.mov *.avi *.wmv *.m4a *.aac *.ogg *.opus *.flac *.wav"),
        ("すべてのファイル", "*.*")
    ]
    input_file = filedialog.askopenfilename(title="変換するメディアファイルを選択", filetypes=filetypes)
    if not input_file:
        return

    supported_formats_list = ["mp3", "wav", "aac", "ogg", "flac", "mp4", "mkv", "mov", "avi"]
    prompt_text = f"出力フォーマットを入力してください (例: {', '.join(supported_formats_list)}):"
    output_format = simpledialog.askstring("出力フォーマット", prompt_text, parent=root)
    if not output_format:
        return
    
    output_format = output_format.lower().strip().replace(".", "")

    output_dir = filedialog.askdirectory(title=f".{output_format}ファイルを保存するディレクトリを選択")
    if not output_dir:
        return

    convert_file(input_file, output_dir, output_format)

if __name__ == "__main__":
    run_converter()
