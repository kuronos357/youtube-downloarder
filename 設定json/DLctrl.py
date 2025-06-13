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
    "comment": "基本設定",
    "directories": [
        "/mnt/chromeos/PlayFiles/Music/BGM",
        "/mnt/chromeos/PlayFiles/Movies",
        "/mnt/chromeos/PlayFiles/Podcasts"
    ],
    "default_directory": "/mnt/chromeos/PlayFiles/Music/BGM",
    "default_format": "mp4",
    "ffmpeg_path": "ffmpeg",
    "log_level": "INFO",
    
    "comment2": "字幕関連設定",
    "download_subtitles": False,
    "embed_subtitles": False,
    "subtitle_languages": ["ja", "en"],
    
    "comment3": "メタデータ設定",
    "write_info_json": True,
    "write_thumbnail": True,
    "ignore_errors": False,
    "no_warnings": False,
    
    "comment4": "品質設定",
    "max_height": 1080,
    "fallback_height": 720,
    "audio_quality": "192",
    
    "comment5": "YouTube制限回避設定",
    "player_clients": ["android", "web", "ios"],
    "skip_formats": ["hls"],
    "enable_android_fallback": True,
    
    "comment6": "プレイリスト設定",
    "mkdir_list": True,
    "makedirector": True,
    
    "comment7": "高度な設定",
    "advanced_options": {
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 1,
        "max_sleep_interval": 5
    },
    
    "comment8": "フォーマット別詳細設定",
    "format_options": {
        "mp4": {
            "primary_format": "best[ext=mp4][height<={max_height}]/best[height<={max_height}]",
            "fallback_format": "best[height<={fallback_height}]/best",
            "description": "MP4形式（推奨）"
        },
        "webm": {
            "primary_format": "best[ext=webm][height<={max_height}]/best[height<={max_height}]",
            "fallback_format": "best[height<={fallback_height}]/best",
            "description": "WebM形式"
        },
        "mp3": {
            "primary_format": "bestaudio[ext=m4a]/bestaudio",
            "fallback_format": "bestaudio/best",
            "postprocessor": {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "{audio_quality}"
            },
            "description": "MP3音声のみ"
        },
        "flac": {
            "primary_format": "bestaudio[ext=m4a]/bestaudio",
            "fallback_format": "bestaudio/best",
            "postprocessor": {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac"
            },
            "description": "FLAC音声（高品質）"
        },
        "best": {
            "primary_format": "best",
            "fallback_format": "best",
            "description": "最高品質"
        }
    }
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
            
            # デフォルト設定で不足分を補完
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            
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
        self.geometry('850x900')  # 初期ウィンドウサイズ
        self.minsize(700, 700)  # 最小ウィンドウサイズ
        self.maxsize(1000, 1400)  # 最大ウィンドウサイズ
        self.resizable(True, True)
        self.config_data = load_config()
        self.dir_widgets = []  # ディレクトリ関連のウィジェット保存用
        self._create_vars()
        self._build_ui()

    def _create_vars(self):
        # 基本設定
        self.dir_var = tk.StringVar(value=self.config_data.get('default_directory', ''))
        self.format_var = tk.StringVar(value=self.config_data.get('default_format', 'mp4'))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path', 'ffmpeg'))
        self.log_level_var = tk.StringVar(value=self.config_data.get('log_level', 'INFO'))
        
        # 字幕関連設定
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles', False))
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles', False))
        self.sub_lang_var = tk.StringVar(value=', '.join(self.config_data.get('subtitle_languages', ['ja', 'en'])))
        
        # メタデータ設定
        self.info_json_var = tk.BooleanVar(value=self.config_data.get('write_info_json', True))
        self.thumbnail_var = tk.BooleanVar(value=self.config_data.get('write_thumbnail', True))
        self.ignore_errors_var = tk.BooleanVar(value=self.config_data.get('ignore_errors', False))
        self.no_warnings_var = tk.BooleanVar(value=self.config_data.get('no_warnings', False))
        
        # 品質設定
        self.max_height_var = tk.IntVar(value=self.config_data.get('max_height', 1080))
        self.fallback_height_var = tk.IntVar(value=self.config_data.get('fallback_height', 720))
        self.audio_quality_var = tk.StringVar(value=self.config_data.get('audio_quality', '192'))
        
        # YouTube制限回避設定
        self.player_clients_var = tk.StringVar(value=', '.join(self.config_data.get('player_clients', ['android', 'web', 'ios'])))
        self.skip_formats_var = tk.StringVar(value=', '.join(self.config_data.get('skip_formats', ['hls'])))
        self.android_fallback_var = tk.BooleanVar(value=self.config_data.get('enable_android_fallback', True))
        
        # プレイリスト設定
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('mkdir_list', True))
        self.makedirector_var = tk.BooleanVar(value=self.config_data.get('makedirector', True))
        
        # 高度な設定
        advanced = self.config_data.get('advanced_options', {})
        self.socket_timeout_var = tk.IntVar(value=advanced.get('socket_timeout', 30))
        self.retries_var = tk.IntVar(value=advanced.get('retries', 3))
        self.fragment_retries_var = tk.IntVar(value=advanced.get('fragment_retries', 3))
        self.sleep_interval_var = tk.IntVar(value=advanced.get('sleep_interval', 1))
        self.max_sleep_interval_var = tk.IntVar(value=advanced.get('max_sleep_interval', 5))

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

        # 各セクションを構築
        self._build_directory_section()
        self._build_basic_settings()
        self._build_subtitle_settings()
        self._build_metadata_settings()
        self._build_quality_settings()
        self._build_youtube_settings()
        self._build_playlist_settings()
        self._build_advanced_settings()
        self._build_buttons()

    def _build_directory_section(self):
        current_row = 0
        
        # ディレクトリセクションのヘッダー
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        
        ttk.Label(header_frame, text='ダウンロード先ディレクトリ:', font=('', 10, 'bold')).grid(row=0, column=0, sticky='w')
        
        # ディレクトリ追加・削除ボタン
        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        ttk.Button(btn_frame, text='+ 追加', command=self.add_directory).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text='- 削除', command=self.remove_directory).grid(row=0, column=1, padx=2)
        
        header_frame.grid_columnconfigure(0, weight=1)

        # ディレクトリリストフレーム
        self.dir_list_frame = ttk.Frame(self.scrollable_frame)
        self.dir_list_frame.grid(row=current_row+1, column=0, columnspan=3, sticky='ew', pady=(0, 20))
        
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

    def _build_basic_settings(self):
        current_row = self._get_next_row()
        
        # 基本設定セクション
        ttk.Label(self.scrollable_frame, text='基本設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(10, 5))
        current_row += 1
        
        # 出力フォーマット
        ttk.Label(self.scrollable_frame, text='出力フォーマット:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        format_frame = ttk.Frame(self.scrollable_frame)
        format_frame.grid(row=current_row, column=1, sticky='w', padx=10)
        
        formats = ['mp3', 'mp4', 'webm', 'flac', 'best']
        for i, fmt in enumerate(formats):
            ttk.Radiobutton(
                format_frame,
                text=fmt,
                variable=self.format_var,
                value=fmt
            ).grid(row=0, column=i, padx=5)
        current_row += 1

        # ffmpegパス
        ttk.Label(self.scrollable_frame, text='ffmpegパス:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        
        ffmpeg_frame = ttk.Frame(self.scrollable_frame)
        ffmpeg_frame.grid(row=current_row, column=1, sticky='ew', padx=10)
        ffmpeg_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_var, width=40).grid(row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(ffmpeg_frame, text='選択', command=self.choose_ffmpeg).grid(row=0, column=1)
        current_row += 1
        
        # ログレベル
        ttk.Label(self.scrollable_frame, text='ログレベル:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        log_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.log_level_var, 
                                values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], state='readonly', width=15)
        log_combo.grid(row=current_row, column=1, sticky='w', padx=10)
        current_row += 1

    def _build_subtitle_settings(self):
        current_row = self._get_next_row()
        
        # 字幕設定セクション
        ttk.Label(self.scrollable_frame, text='字幕設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='字幕をダウンロード', variable=self.sub_dl_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='字幕を埋め込み', variable=self.sub_embed_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='字幕言語 (カンマ区切り):').grid(
            row=current_row, column=0, sticky='w', padx=20)
        ttk.Entry(self.scrollable_frame, textvariable=self.sub_lang_var, width=30).grid(
            row=current_row, column=1, sticky='w', padx=10)
        current_row += 1

    def _build_metadata_settings(self):
        current_row = self._get_next_row()
        
        # メタデータ設定セクション
        ttk.Label(self.scrollable_frame, text='メタデータ設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='情報JSONファイルを作成', variable=self.info_json_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='サムネイルを保存', variable=self.thumbnail_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='エラーを無視', variable=self.ignore_errors_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='警告を非表示', variable=self.no_warnings_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1

    def _build_quality_settings(self):
        current_row = self._get_next_row()
        
        # 品質設定セクション
        ttk.Label(self.scrollable_frame, text='品質設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='最大解像度 (高さ):').grid(
            row=current_row, column=0, sticky='w', padx=20)
        height_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.max_height_var, 
                                   values=[480, 720, 1080, 1440, 2160], width=10)
        height_combo.grid(row=current_row, column=1, sticky='w', padx=10)
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='フォールバック解像度:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        fallback_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.fallback_height_var, 
                                     values=[360, 480, 720, 1080], width=10)
        fallback_combo.grid(row=current_row, column=1, sticky='w', padx=10)
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='音声品質 (kbps):').grid(
            row=current_row, column=0, sticky='w', padx=20)
        audio_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.audio_quality_var, 
                                  values=['128', '192', '256', '320'], width=10)
        audio_combo.grid(row=current_row, column=1, sticky='w', padx=10)
        current_row += 1

    def _build_youtube_settings(self):
        current_row = self._get_next_row()
        
        # YouTube制限回避設定セクション
        ttk.Label(self.scrollable_frame, text='YouTube制限回避設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='プレイヤークライアント:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        ttk.Entry(self.scrollable_frame, textvariable=self.player_clients_var, width=30).grid(
            row=current_row, column=1, sticky='w', padx=10)
        current_row += 1
        
        ttk.Label(self.scrollable_frame, text='スキップフォーマット:').grid(
            row=current_row, column=0, sticky='w', padx=20)
        ttk.Entry(self.scrollable_frame, textvariable=self.skip_formats_var, width=30).grid(
            row=current_row, column=1, sticky='w', padx=10)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='Androidフォールバックを有効', variable=self.android_fallback_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1

    def _build_playlist_settings(self):
        current_row = self._get_next_row()
        
        # プレイリスト設定セクション
        ttk.Label(self.scrollable_frame, text='プレイリスト設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='プレイリスト用ディレクトリを作成', variable=self.makedir_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.scrollable_frame, text='makedirector機能を有効', variable=self.makedirector_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1

    def _build_advanced_settings(self):
        current_row = self._get_next_row()
        
        # 高度な設定セクション
        ttk.Label(self.scrollable_frame, text='高度な設定:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        settings = [
            ('ソケットタイムアウト (秒):', self.socket_timeout_var),
            ('リトライ回数:', self.retries_var),
            ('フラグメントリトライ回数:', self.fragment_retries_var),
            ('スリープ間隔 (秒):', self.sleep_interval_var),
            ('最大スリープ間隔 (秒):', self.max_sleep_interval_var)
        ]
        
        for label_text, var in settings:
            ttk.Label(self.scrollable_frame, text=label_text).grid(
                row=current_row, column=0, sticky='w', padx=20)
            ttk.Spinbox(self.scrollable_frame, from_=1, to=300, textvariable=var, width=10).grid(
                row=current_row, column=1, sticky='w', padx=10)
            current_row += 1

    def _build_buttons(self):
        current_row = self._get_next_row()
        
        # ボタンセクション
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.grid(row=current_row, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text='保存', command=self.on_save).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='設定ファイルを開く', command=self.open_config).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text='リセット', command=self.reset_config).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text='終了', command=self.destroy).grid(row=0, column=3, padx=5)

    def _get_next_row(self):
        # スクロール可能フレーム内の次の行を取得
        children = self.scrollable_frame.winfo_children()
        if not children:
            return 0
        max_row = 0
        for child in children:
            info = child.grid_info()
            if info and 'row' in info:
                max_row = max(max_row, info['row'])
        return max_row + 1

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

    def choose_ffmpeg(self):
        path = filedialog.askopenfilename(
            title="ffmpegの実行ファイルを選択",
            filetypes=[('実行ファイル', '*.exe'), ('全てのファイル', '*.*')]
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

    def reset_config(self):
        if messagebox.askyesno('確認', '設定をデフォルトに戻しますか？'):
            self.config_data = DEFAULT_CONFIG.copy()
            self._update_vars_from_config()
            self._refresh_directory_list()
            messagebox.showinfo('リセット', '設定をデフォルトに戻しました。')

    def _update_vars_from_config(self):
        """設定データからGUI変数を更新"""
        # 基本設定
        self.dir_var.set(self.config_data.get('default_directory', ''))
        self.format_var.set(self.config_data.get('default_format', 'mp4'))
        self.ffmpeg_var.set(self.config_data.get('ffmpeg_path', 'ffmpeg'))
        self.log_level_var.set(self.config_data.get('log_level', 'INFO'))
        
        # 字幕関連設定
        self.sub_dl_var.set(self.config_data.get('download_subtitles', False))
        self.sub_embed_var.set(self.config_data.get('embed_subtitles', False))
        self.sub_lang_var.set(', '.join(self.config_data.get('subtitle_languages', ['ja', 'en'])))
        
        # メタデータ設定
        self.info_json_var.set(self.config_data.get('write_info_json', True))
        self.thumbnail_var.set(self.config_data.get('write_thumbnail', True))
        self.ignore_errors_var.set(self.config_data.get('ignore_errors', False))
        self.no_warnings_var.set(self.config_data.get('no_warnings', False))
        
        # 品質設定
        self.max_height_var.set(self.config_data.get('max_height', 1080))
        self.fallback_height_var.set(self.config_data.get('fallback_height', 720))
        self.audio_quality_var.set(self.config_data.get('audio_quality', '192'))
        
        # YouTube制限回避設定
        self.player_clients_var.set(', '.join(self.config_data.get('player_clients', ['android', 'web', 'ios'])))
        self.skip_formats_var.set(', '.join(self.config_data.get('skip_formats', ['hls'])))
        self.android_fallback_var.set(self.config_data.get('enable_android_fallback', True))
        
        # プレイリスト設定
        self.makedir_var.set(self.config_data.get('mkdir_list', True))
        self.makedirector_var.set(self.config_data.get('makedirector', True))
        
        # 高度な設定
        advanced = self.config_data.get('advanced_options', {})
        self.socket_timeout_var.set(advanced.get('socket_timeout', 30))
        self.retries_var.set(advanced.get('retries', 3))
        self.fragment_retries_var.set(advanced.get('fragment_retries', 3))
        self.sleep_interval_var.set(advanced.get('sleep_interval', 1))
        self.max_sleep_interval_var.set(advanced.get('max_sleep_interval', 5))

    def on_save(self):
        """設定を保存"""
        try:
            # 基本設定
            self.config_data['default_directory'] = self.dir_var.get()
            self.config_data['default_format'] = self.format_var.get()
            self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
            self.config_data['log_level'] = self.log_level_var.get()
            
            # 字幕関連設定
            self.config_data['download_subtitles'] = self.sub_dl_var.get()
            self.config_data['embed_subtitles'] = self.sub_embed_var.get()
            
            # 字幕言語をリストに変換
            sub_langs = [lang.strip() for lang in self.sub_lang_var.get().split(',') if lang.strip()]
            self.config_data['subtitle_languages'] = sub_langs if sub_langs else ['ja', 'en']
            
            # メタデータ設定
            self.config_data['write_info_json'] = self.info_json_var.get()
            self.config_data['write_thumbnail'] = self.thumbnail_var.get()
            self.config_data['ignore_errors'] = self.ignore_errors_var.get()
            self.config_data['no_warnings'] = self.no_warnings_var.get()
            
            # 品質設定
            self.config_data['max_height'] = self.max_height_var.get()
            self.config_data['fallback_height'] = self.fallback_height_var.get()
            self.config_data['audio_quality'] = self.audio_quality_var.get()
            
            # YouTube制限回避設定
            player_clients = [client.strip() for client in self.player_clients_var.get().split(',') if client.strip()]
            self.config_data['player_clients'] = player_clients if player_clients else ['android', 'web', 'ios']
            
            skip_formats = [fmt.strip() for fmt in self.skip_formats_var.get().split(',') if fmt.strip()]
            self.config_data['skip_formats'] = skip_formats if skip_formats else ['hls']
            
            self.config_data['enable_android_fallback'] = self.android_fallback_var.get()
            
            # プレイリスト設定
            self.config_data['mkdir_list'] = self.makedir_var.get()
            self.config_data['makedirector'] = self.makedirector_var.get()
            
            # 高度な設定
            self.config_data['advanced_options'] = {
                'socket_timeout': self.socket_timeout_var.get(),
                'retries': self.retries_var.get(),
                'fragment_retries': self.fragment_retries_var.get(),
                'sleep_interval': self.sleep_interval_var.get(),
                'max_sleep_interval': self.max_sleep_interval_var.get()
            }
            
            # 設定を保存
            save_config(self.config_data)
            messagebox.showinfo('保存', '設定を保存しました。')
            
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存中にエラーが発生しました: {e}')

if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()