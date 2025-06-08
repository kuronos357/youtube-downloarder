import json  # JSON形式で設定を保存・読み込みするためのモジュール
import os
import sys
import subprocess  # システムコマンドを実行するためのモジュール
import tkinter as tk  # GUIの作成に使用
from tkinter import ttk, filedialog, messagebox  # GUI用のウィジェットやダイアログ
from pathlib import Path  # ファイルパス操作用

# 設定ファイルのパスを生成（現在のファイルと同じディレクトリに配置）
CONFIG_FILE = Path(__file__).parent / 'config.json'

# 設定ファイルが存在しない場合のデフォルト設定
DEFAULT_CONFIG = {
    "directories": [
        "/mnt/chromeos/PlayFiles/Music/BGM",
        "/mnt/chromeos/PlayFiles/Movies",
        "/mnt/chromeos/PlayFiles/Podcasts"
    ],
    "default_directory": "/mnt/chromeos/PlayFiles/Music/BGM",
    "default_format": "mp3",
    "ffmpeg_path": "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe",
    "download_subtitles": False,
    "embed_subtitles": False,
    "makedirector": True
}

# 設定ファイルを読み込む関数
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 古い形式から新しい形式への変換
            if 'directory1' in config:
                directories = []
                i = 1
                while f'directory{i}' in config:
                    directories.append(config[f'directory{i}'])
                    i += 1
                config['directories'] = directories
                # 古いキーを削除
                for j in range(1, i):
                    config.pop(f'directory{j}', None)
            return config
    return DEFAULT_CONFIG.copy()

# 設定ファイルに設定情報を書き込む関数
def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# ConfigGUIクラス: 設定画面のためのメインウィンドウクラス
class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('設定マネージャー')
        self.geometry('800x800')  # 初期ウィンドウサイズ
        self.minsize(600, 600)  # 最小ウィンドウサイズ
        self.maxsize(800, 1200)  # 最大ウィンドウサイズ
        # self.iconbitmap('icon.ico')  # アイコンファイルのパスを指定（必要に応じて変更）
        self.resizable(True, True)
        self.config_data = load_config()
        self.dir_widgets = []  # ディレクトリ関連のウィジェット保存用
        self._create_vars()
        self._build_ui()

    def _create_vars(self):
        self.dir_var = tk.StringVar(value=self.config_data.get('default_directory', ''))
        self.format_var = tk.StringVar(value=self.config_data.get('default_format', 'mp3'))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path', ''))
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles', False))
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles', False))
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('mkdir_list', True))

    def _build_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(sticky='nsew')
        
        # スクロール可能なフレームの設定
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_directory_section()
        self._build_other_sections()

    def _build_directory_section(self):
        # ディレクトリセクションのヘッダー
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        
        ttk.Label(header_frame, text='ダウンロード先ディレクトリ:', font=('', 10, 'bold')).grid(row=0, column=0, sticky='w')
        
        # ディレクトリ追加・削除ボタン
        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        ttk.Button(btn_frame, text='+ 追加', command=self.add_directory).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text='- 削除', command=self.remove_directory).grid(row=0, column=1, padx=2)
        
        header_frame.grid_columnconfigure(0, weight=1)

        # ディレクトリリストフレーム
        self.dir_list_frame = ttk.Frame(self.scrollable_frame)
        self.dir_list_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0, 20))
        
        self._refresh_directory_list()

    def _refresh_directory_list(self):
        # 既存のウィジェットをクリア
        for widget in self.dir_list_frame.winfo_children():
            widget.destroy()
        self.dir_widgets.clear()

        # ディレクトリリストを再構築
        directories = self.config_data.get('directories', [])
        for i, directory in enumerate(directories):
            self._create_directory_widget(i, directory)

    def _create_directory_widget(self, index, directory):
        frame = ttk.Frame(self.dir_list_frame)
        frame.grid(row=index, column=0, columnspan=3, sticky='ew', pady=2)
        frame.grid_columnconfigure(0, weight=1)
        
        # ラジオボタン
        rb = ttk.Radiobutton(
            frame,
            text=f'候補{index+1}: {directory}',
            variable=self.dir_var,
            value=directory
        )
        rb.grid(row=0, column=0, sticky='w')
        
        # 変更ボタン
        change_btn = ttk.Button(
            frame,
            text='変更',
            command=lambda idx=index: self.change_directory(idx)
        )
        change_btn.grid(row=0, column=1, padx=5)
        
        self.dir_widgets.append({
            'frame': frame,
            'radiobutton': rb,
            'button': change_btn,
            'index': index
        })

    def add_directory(self):
        # 新しいディレクトリを追加
        new_path = filedialog.askdirectory(title="新しいディレクトリを選択")
        if new_path:
            directories = self.config_data.get('directories', [])
            directories.append(new_path)
            self.config_data['directories'] = directories
            self._refresh_directory_list()

    def remove_directory(self):
        directories = self.config_data.get('directories', [])
        if len(directories) <= 1:
            messagebox.showwarning('警告', '最低1つのディレクトリは必要です。')
            return
        
        # 現在選択されているディレクトリのインデックスを取得
        current_dir = self.dir_var.get()
        try:
            remove_index = directories.index(current_dir)
        except ValueError:
            # 選択されていない場合は最後のディレクトリを削除
            remove_index = len(directories) - 1
        
        # 確認ダイアログ
        if messagebox.askyesno('確認', f'候補{remove_index+1}のディレクトリを削除しますか？\n{directories[remove_index]}'):
            directories.pop(remove_index)
            self.config_data['directories'] = directories
            
            # 削除されたディレクトリが選択されていた場合、最初のディレクトリを選択
            if current_dir not in directories and directories:
                self.dir_var.set(directories[0])
            
            self._refresh_directory_list()

    def change_directory(self, index):
        new_path = filedialog.askdirectory(title=f"候補{index+1}のディレクトリを変更")
        if new_path:
            directories = self.config_data.get('directories', [])
            old_path = directories[index]
            directories[index] = new_path
            self.config_data['directories'] = directories
            
            # 選択されているディレクトリが変更された場合、選択を更新
            if self.dir_var.get() == old_path:
                self.dir_var.set(new_path)
            
            self._refresh_directory_list()

    def _build_other_sections(self):
        current_row = 2
        
        # 出力フォーマットセクション
        ttk.Label(self.scrollable_frame, text='出力フォーマット:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(10, 5))
        current_row += 1
        
        formats = ['mp3', 'webm', 'mp4']
        for fmt in formats:
            ttk.Radiobutton(
                self.scrollable_frame,
                text=fmt,
                variable=self.format_var,
                value=fmt
            ).grid(row=current_row, column=0, sticky='w', padx=20)
            current_row += 1

        # ffmpegパスセクション
        ttk.Label(self.scrollable_frame, text='ffmpegパス:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(10, 5))
        current_row += 1
        
        ffmpeg_frame = ttk.Frame(self.scrollable_frame)
        ffmpeg_frame.grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=2)
        ffmpeg_frame.grid_columnconfigure(0, weight=1)
        
        entry = ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_var, width=50)
        entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(ffmpeg_frame, text='選択', command=self.choose_ffmpeg).grid(row=0, column=1)
        current_row += 1

        # 字幕・その他設定セクション
        ttk.Label(self.scrollable_frame, text='その他の設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='字幕をダウンロード', variable=self.sub_dl_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='字幕を埋め込み', variable=self.sub_embed_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='プレイリストの場合のディレクトリ作成する', variable=self.makedir_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1

        # ボタンセクション
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.grid(row=current_row, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text='保存', command=self.on_save).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='設定ファイルを開く', command=self.open_config).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text='終了', command=self.destroy).grid(row=0, column=2, padx=5)

    def choose_ffmpeg(self):
        path = filedialog.askopenfilename(filetypes=[('Executable', '*.exe'), ('All files', '*.*')])
        if path:
            self.ffmpeg_var.set(path)

    def open_config(self):
        try:
            if os.name == 'nt':
                os.startfile(CONFIG_FILE)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(CONFIG_FILE)])
            else:
                subprocess.Popen(['xdg-open', str(CONFIG_FILE)])
        except Exception as e:
            messagebox.showerror('エラー', f'設定ファイルを開けませんでした: {e}')

    def on_save(self):
        self.config_data['default_directory'] = self.dir_var.get()
        self.config_data['default_format'] = self.format_var.get()
        self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
        self.config_data['download_subtitles'] = self.sub_dl_var.get()
        self.config_data['embed_subtitles'] = self.sub_embed_var.get()
        self.config_data['mkdir_list'] = self.makedir_var.get()
        
        save_config(self.config_data)
        messagebox.showinfo('保存', '設定を保存しました。')

if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()