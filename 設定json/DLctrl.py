import json  
import os
import sys
import subprocess  # システムコマンドを実行するためのモジュール
import tkinter as tk  
from tkinter import ttk, filedialog, messagebox  # GUI用のウィジェットやダイアログ
from pathlib import Path  # ファイルパス操作用

# 設定ファイルのパスを生成（現在のファイルと同じディレクトリに配置）
CONFIG_FILE = Path(__file__).parent / 'config.json'

# 設定ファイルが存在しない場合のデフォルト設定
DEFAULT_CONFIG = {
    "directories": [
        {"path": "/mnt/chromeos/PlayFiles/Music/BGM", "format": "mp3"},
        {"path": "/mnt/chromeos/PlayFiles/Movies", "format": "mp4"},
        {"path": "/mnt/chromeos/PlayFiles/Podcasts", "format": "mp3"}
    ],
    "default_directory_index": 0,
    "interactive_selection": False,
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
                for i in range(1, 4):
                    dir_key = f'directory{i}'
                    if dir_key in config:
                        directories.append({
                            "path": config[dir_key],
                            "format": config.get('default_format', 'mp3')
                        })
                config['directories'] = directories
                config['default_directory_index'] = 0
                # 古いキーを削除
                for key in ['directory1', 'directory2', 'directory3', 'default_directory', 'default_format']:
                    config.pop(key, None)
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
        self.geometry('1000x800')  # ウィンドウの初期サイズを設定
        self.resizable(True, True)
        self.config_data = load_config()
        self.dir_widgets = []  # ディレクトリ用ウィジェットのリスト
        self._create_vars()
        self._build_ui()

    def _create_vars(self):
        self.dir_var = tk.IntVar(value=self.config_data.get('default_directory_index', 0))
        self.interactive_var = tk.BooleanVar(value=self.config_data.get('interactive_selection', False))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path', ''))
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles', False))
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles', False))
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('makedirector', True))

    def _build_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        # ダウンロード先ディレクトリの設定セクション
        dir_section = ttk.LabelFrame(main_frame, text='ダウンロード先ディレクトリ', padding=5)
        dir_section.pack(fill='both', expand=True, pady=(0, 10))

        # ディレクトリ管理ボタン
        btn_frame = ttk.Frame(dir_section)
        btn_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(btn_frame, text='ディレクトリを追加', command=self.add_directory).pack(side='left')
        ttk.Label(btn_frame, text='※ディレクトリを追加後、パスを設定してください').pack(side='left', padx=(10, 0))

        # スクロール可能なフレーム
        canvas = tk.Canvas(dir_section, height=200)
        scrollbar = ttk.Scrollbar(dir_section, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        # スクロール設定
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<MouseWheel>", on_mousewheel)

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ディレクトリリストを構築
        self._build_directory_list()

        # ディレクトリ選択モード設定
        mode_frame = ttk.LabelFrame(main_frame, text="ディレクトリ選択モード", padding=5)
        mode_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Radiobutton(
            mode_frame, 
            text="json準拠の設定", 
            variable=self.interactive_var, 
            value=False
        ).pack(anchor='w')
        
        ttk.Radiobutton(
            mode_frame, 
            text="実行時に対話的選択", 
            variable=self.interactive_var, 
            value=True
        ).pack(anchor='w')

        # その他の設定セクション
        other_frame = ttk.LabelFrame(main_frame, text="その他の設定", padding=5)
        other_frame.pack(fill='x', pady=(0, 10))

        # ffmpegパス設定
        ffmpeg_frame = ttk.Frame(other_frame)
        ffmpeg_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(ffmpeg_frame, text='ffmpegパス:').pack(anchor='w')
        
        ffmpeg_entry_frame = ttk.Frame(ffmpeg_frame)
        ffmpeg_entry_frame.pack(fill='x', pady=(2, 0))
        ttk.Entry(ffmpeg_entry_frame, textvariable=self.ffmpeg_var).pack(side='left', fill='x', expand=True)
        ttk.Button(ffmpeg_entry_frame, text='選択', command=self.choose_ffmpeg).pack(side='right', padx=(5, 0))

        # 字幕関連の設定
        ttk.Checkbutton(other_frame, text='字幕をダウンロード', variable=self.sub_dl_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(other_frame, text='字幕を埋め込み', variable=self.sub_embed_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(other_frame, text='プレイリストの場合のディレクトリ作成する', variable=self.makedir_var).pack(anchor='w', pady=2)

        # ボタンフレーム
        bottom_btn_frame = ttk.Frame(main_frame)
        bottom_btn_frame.pack(fill='x', pady=(10, 0))
        
        # 「保存して終了」ボタンに統合
        ttk.Button(bottom_btn_frame, text='保存して終了', command=self.on_save_and_exit).pack(side='left', padx=(0, 5))
        ttk.Button(bottom_btn_frame, text='設定ファイルを開く', command=self.open_config).pack(side='left', padx=5)

    def _build_directory_list(self):
        # 既存のウィジェットをクリア
        for widgets in self.dir_widgets:
            if 'frame' in widgets and widgets['frame'].winfo_exists():
                widgets['frame'].destroy()
        self.dir_widgets.clear()

        # ディレクトリごとにウィジェットを作成
        for i, dir_info in enumerate(self.config_data['directories']):
            self._create_directory_row(i, dir_info)
        
        # スクロール領域を更新
        self.scrollable_frame.update_idletasks()

    def _create_directory_row(self, index, dir_info):
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill='x', pady=2, padx=5)

        # すべてを1行に配置
        # ラジオボタン
        radio = ttk.Radiobutton(
            row_frame,
            text=f"候補{index + 1}",
            variable=self.dir_var,
            value=index
        )
        radio.pack(side='left')

        # パス表示・編集エントリ
        path_var = tk.StringVar(value=dir_info['path'])
        path_entry = ttk.Entry(row_frame, textvariable=path_var, width=40)
        path_entry.pack(side='left', fill='x', expand=True, padx=(5, 0))

        # フォーマット選択
        format_var = tk.StringVar(value=dir_info['format'])
        format_combo = ttk.Combobox(
            row_frame,
            textvariable=format_var,
            values=['mp3', 'mp4', 'webm', 'wav', 'flac'],
            width=8,
            state='readonly'
        )
        format_combo.pack(side='right', padx=(5, 0))

        # 選択ボタン
        select_btn = ttk.Button(
            row_frame,
            text='選択',
            command=lambda idx=index: self.change_dir(idx)
        )
        select_btn.pack(side='right', padx=(5, 0))

        # 削除ボタン（2個以上ある場合のみ表示）
        delete_btn = None
        if len(self.config_data['directories']) > 1:
            delete_btn = ttk.Button(
                row_frame,
                text='削除',
                command=lambda idx=index: self.delete_directory(idx)
            )
            delete_btn.pack(side='right', padx=(5, 0))

        # ウィジェットを保存
        widgets = {
            'frame': row_frame,
            'radio': radio,
            'path_var': path_var,
            'path_entry': path_entry,
            'format_var': format_var,
            'format_combo': format_combo,
            'select_btn': select_btn,
            'delete_btn': delete_btn
        }
        self.dir_widgets.append(widgets)

    def add_directory(self):
        # 新しいディレクトリを追加
        new_dir = {"path": "", "format": "mp3"}
        self.config_data['directories'].append(new_dir)
        self._build_directory_list()
        
        # 追加されたことを視覚的に示す
        messagebox.showinfo('追加完了', f'新しいディレクトリ候補{len(self.config_data["directories"])}を追加しました。\nパスを設定してください。')

    def delete_directory(self, index):
        # ディレクトリを削除（最低1個は残す）
        if len(self.config_data['directories']) <= 1:
            messagebox.showwarning('警告', '最低1つのディレクトリは必要です。')
            return
        
        # 確認ダイアログ
        dir_path = self.config_data['directories'][index]['path']
        dir_name = dir_path if dir_path else f"候補{index + 1}"
        
        if messagebox.askyesno('確認', f'"{dir_name}"を削除しますか？'):
            self.config_data['directories'].pop(index)
            
            # 選択中のインデックスを調整
            current_index = self.dir_var.get()
            if current_index >= len(self.config_data['directories']):
                self.dir_var.set(len(self.config_data['directories']) - 1)
            elif current_index > index:
                self.dir_var.set(current_index - 1)
            
            self._build_directory_list()

    def change_dir(self, index):
        # ディレクトリ選択ダイアログ
        new_path = filedialog.askdirectory(title=f'候補{index + 1}のディレクトリを選択')
        if new_path:
            self.dir_widgets[index]['path_var'].set(new_path)

    def choose_ffmpeg(self):
        path = filedialog.askopenfilename(
            title='ffmpegの実行ファイルを選択',
            filetypes=[('Executable', '*.exe'), ('All files', '*.*')]
        )
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
        # GUI上の設定値を設定データに反映
        directories = []
        for widgets in self.dir_widgets:
            path = widgets['path_var'].get().strip()
            format_val = widgets['format_var'].get()
            if path:  # 空でないパスのみ保存
                directories.append({"path": path, "format": format_val})
        
        if not directories:
            messagebox.showwarning('警告', '最低1つのディレクトリを設定してください。')
            return
        
        self.config_data['directories'] = directories
        self.config_data['default_directory_index'] = min(self.dir_var.get(), len(directories) - 1)
        self.config_data['interactive_selection'] = self.interactive_var.get()
        self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
        self.config_data['download_subtitles'] = self.sub_dl_var.get()
        self.config_data['embed_subtitles'] = self.sub_embed_var.get()
        self.config_data['makedirector'] = self.makedir_var.get()
        
        try:
            save_config(self.config_data)
            print('保存完了', '設定を保存しました。')
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存に失敗しました: {e}')

    def on_save_and_exit(self):
        self.on_save()
        self.destroy()

# メイン処理
if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()