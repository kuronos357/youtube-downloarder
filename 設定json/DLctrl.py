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
    "makedirector": True,
    # 新しい設定項目
    "subtitle_languages": ["ja", "en"],
    "write_info_json": True,
    "write_thumbnail": True,
    "max_height": 1080,
    "fallback_height": 720,
    "audio_quality": "192",
    "player_clients": ["android", "web", "ios"],
    "skip_formats": ["hls"],
    "enable_android_fallback": True,
    "format_options": {
        "mp4": {
            "primary_format": "best[ext=mp4][height<={max_height}]/best[ext=mp4]",
            "fallback_format": "best[height<={fallback_height}]/best",
            "description": "MP4形式（推奨）"
        },
        "webm": {
            "primary_format": "best[ext=webm][height<={max_height}]/best[ext=webm]",
            "fallback_format": "best[height<={fallback_height}]/best",
            "description": "WebM形式"
        },
        "mp3": {
            "primary_format": "bestaudio[ext=m4a]/bestaudio",
            "fallback_format": "bestaudio/best",
            "description": "MP3音声形式"
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
            
            # デフォルト設定で不足している項目を補完
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
        self.title('YouTube Downloader 設定マネージャー')
        self.geometry('900x900')  # 初期ウィンドウサイズ
        self.minsize(800, 700)  # 最小ウィンドウサイズ
        self.maxsize(1000, 1400)  # 最大ウィンドウサイズ
        self.resizable(True, True)
        self.config_data = load_config()
        self.dir_widgets = []  # ディレクトリ関連のウィジェット保存用
        self._create_vars()
        self._build_ui()

    def _create_vars(self):
        # 既存の変数
        self.dir_var = tk.StringVar(value=self.config_data.get('default_directory', ''))
        self.format_var = tk.StringVar(value=self.config_data.get('default_format', 'mp3'))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path', ''))
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles', False))
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles', False))
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('makedirector', True))
        
        # 新しい変数
        self.sub_lang_var = tk.StringVar(value=','.join(self.config_data.get('subtitle_languages', ['ja', 'en'])))
        self.info_json_var = tk.BooleanVar(value=self.config_data.get('write_info_json', True))
        self.thumbnail_var = tk.BooleanVar(value=self.config_data.get('write_thumbnail', True))
        self.max_height_var = tk.StringVar(value=str(self.config_data.get('max_height', 1080)))
        self.fallback_height_var = tk.StringVar(value=str(self.config_data.get('fallback_height', 720)))
        self.audio_quality_var = tk.StringVar(value=str(self.config_data.get('audio_quality', '192')))
        self.player_clients_var = tk.StringVar(value=','.join(self.config_data.get('player_clients', ['android', 'web', 'ios'])))
        self.skip_formats_var = tk.StringVar(value=','.join(self.config_data.get('skip_formats', ['hls'])))
        self.android_fallback_var = tk.BooleanVar(value=self.config_data.get('enable_android_fallback', True))

    def _build_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(sticky='nsew')
        
        # タブコントロール
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        
        # タブの作成
        self.basic_tab = ttk.Frame(self.notebook)
        self.quality_tab = ttk.Frame(self.notebook)
        self.advanced_tab = ttk.Frame(self.notebook)
        self.format_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.basic_tab, text='基本設定')
        self.notebook.add(self.quality_tab, text='品質設定')
        self.notebook.add(self.advanced_tab, text='高度な設定')
        self.notebook.add(self.format_tab, text='フォーマット設定')
        
        # 各タブの内容を構築
        self._build_basic_tab()
        self._build_quality_tab()
        self._build_advanced_tab()
        self._build_format_tab()
        
        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, pady=10)
        
        ttk.Button(btn_frame, text='保存', command=self.on_save).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='設定ファイルを開く', command=self.open_config).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text='デフォルトに戻す', command=self.reset_to_default).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text='終了', command=self.destroy).grid(row=0, column=3, padx=5)
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _build_basic_tab(self):
        # スクロール可能なフレームの設定
        canvas = tk.Canvas(self.basic_tab)
        scrollbar = ttk.Scrollbar(self.basic_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.basic_tab.grid_rowconfigure(0, weight=1)
        self.basic_tab.grid_columnconfigure(0, weight=1)
        
        self.basic_scrollable_frame = scrollable_frame
        
        # ディレクトリセクション
        self._build_directory_section_basic()
        
        # フォーマットセクション
        self._build_format_section_basic()
        
        # ffmpegパスセクション
        self._build_ffmpeg_section_basic()
        
        # 基本的な字幕・その他設定
        self._build_basic_options_section()

    def _build_directory_section_basic(self):
        current_row = 0
        
        # ディレクトリセクションのヘッダー
        header_frame = ttk.Frame(self.basic_scrollable_frame)
        header_frame.grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        
        ttk.Label(header_frame, text='ダウンロード先ディレクトリ:', font=('', 10, 'bold')).grid(row=0, column=0, sticky='w')
        
        # ディレクトリ追加・削除ボタン
        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        ttk.Button(btn_frame, text='+ 追加', command=self.add_directory).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text='- 削除', command=self.remove_directory).grid(row=0, column=1, padx=2)
        
        header_frame.grid_columnconfigure(0, weight=1)
        current_row += 1

        # ディレクトリリストフレーム
        self.dir_list_frame = ttk.Frame(self.basic_scrollable_frame)
        self.dir_list_frame.grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=(0, 20))
        
        self._refresh_directory_list()

    def _build_format_section_basic(self):
        current_row = 2
        
        # 出力フォーマットセクション
        ttk.Label(self.basic_scrollable_frame, text='出力フォーマット:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(10, 5))
        current_row += 1
        
        formats = ['mp3', 'webm', 'mp4']
        for fmt in formats:
            ttk.Radiobutton(
                self.basic_scrollable_frame,
                text=fmt,
                variable=self.format_var,
                value=fmt
            ).grid(row=current_row, column=0, sticky='w', padx=20)
            current_row += 1

    def _build_ffmpeg_section_basic(self):
        current_row = 6
        
        # ffmpegパスセクション
        ttk.Label(self.basic_scrollable_frame, text='ffmpegパス:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(10, 5))
        current_row += 1
        
        ffmpeg_frame = ttk.Frame(self.basic_scrollable_frame)
        ffmpeg_frame.grid(row=current_row, column=0, columnspan=3, sticky='ew', pady=2)
        ffmpeg_frame.grid_columnconfigure(0, weight=1)
        
        entry = ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_var, width=50)
        entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(ffmpeg_frame, text='選択', command=self.choose_ffmpeg).grid(row=0, column=1)

    def _build_basic_options_section(self):
        current_row = 8
        
        # 基本オプションセクション
        ttk.Label(self.basic_scrollable_frame, text='基本オプション:', font=('', 10, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(15, 5))
        current_row += 1
        
        ttk.Checkbutton(self.basic_scrollable_frame, text='字幕をダウンロード', variable=self.sub_dl_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.basic_scrollable_frame, text='字幕を埋め込み', variable=self.sub_embed_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.basic_scrollable_frame, text='プレイリストの場合のディレクトリ作成する', variable=self.makedir_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.basic_scrollable_frame, text='情報JSONファイルを作成', variable=self.info_json_var).grid(
            row=current_row, column=0, sticky='w', padx=20)
        current_row += 1
        
        ttk.Checkbutton(self.basic_scrollable_frame, text='サムネイルを保存', variable=self.thumbnail_var).grid(
            row=current_row, column=0, sticky='w', padx=20)

    def _build_quality_tab(self):
        frame = ttk.Frame(self.quality_tab, padding=20)
        frame.grid(sticky='nsew')
        self.quality_tab.grid_rowconfigure(0, weight=1)
        self.quality_tab.grid_columnconfigure(0, weight=1)
        
        current_row = 0
        
        # 品質設定セクション
        ttk.Label(frame, text='品質設定', font=('', 12, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(0, 10))
        current_row += 1
        
        # 最大解像度
        ttk.Label(frame, text='最大解像度 (高さ):').grid(
            row=current_row, column=0, sticky='w', pady=5)
        height_frame = ttk.Frame(frame)
        height_frame.grid(row=current_row, column=1, sticky='w', padx=10)
        ttk.Entry(height_frame, textvariable=self.max_height_var, width=10).grid(row=0, column=0)
        ttk.Label(height_frame, text='px').grid(row=0, column=1, padx=(5, 0))
        current_row += 1
        
        # フォールバック解像度
        ttk.Label(frame, text='フォールバック解像度 (高さ):').grid(
            row=current_row, column=0, sticky='w', pady=5)
        fallback_frame = ttk.Frame(frame)
        fallback_frame.grid(row=current_row, column=1, sticky='w', padx=10)
        ttk.Entry(fallback_frame, textvariable=self.fallback_height_var, width=10).grid(row=0, column=0)
        ttk.Label(fallback_frame, text='px').grid(row=0, column=1, padx=(5, 0))
        current_row += 1
        
        # 音声品質
        ttk.Label(frame, text='音声品質 (kbps):').grid(
            row=current_row, column=0, sticky='w', pady=5)
        audio_frame = ttk.Frame(frame)
        audio_frame.grid(row=current_row, column=1, sticky='w', padx=10)
        quality_combo = ttk.Combobox(audio_frame, textvariable=self.audio_quality_var, 
                                   values=['128', '192', '256', '320'], width=10)
        quality_combo.grid(row=0, column=0)
        ttk.Label(audio_frame, text='kbps').grid(row=0, column=1, padx=(5, 0))
        current_row += 1

    def _build_advanced_tab(self):
        frame = ttk.Frame(self.advanced_tab, padding=20)
        frame.grid(sticky='nsew')
        self.advanced_tab.grid_rowconfigure(0, weight=1)
        self.advanced_tab.grid_columnconfigure(0, weight=1)
        
        current_row = 0
        
        # 高度な設定セクション
        ttk.Label(frame, text='YouTube制限回避設定', font=('', 12, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(0, 10))
        current_row += 1
        
        # プレイヤークライアント
        ttk.Label(frame, text='プレイヤークライアント:').grid(
            row=current_row, column=0, sticky='w', pady=5)
        ttk.Entry(frame, textvariable=self.player_clients_var, width=40).grid(
            row=current_row, column=1, sticky='w', padx=10)
        ttk.Label(frame, text='(カンマ区切り)', font=('', 8)).grid(
            row=current_row, column=2, sticky='w', padx=5)
        current_row += 1
        
        # スキップフォーマット
        ttk.Label(frame, text='スキップフォーマット:').grid(
            row=current_row, column=0, sticky='w', pady=5)
        ttk.Entry(frame, textvariable=self.skip_formats_var, width=40).grid(
            row=current_row, column=1, sticky='w', padx=10)
        ttk.Label(frame, text='(カンマ区切り)', font=('', 8)).grid(
            row=current_row, column=2, sticky='w', padx=5)
        current_row += 1
        
        # Androidフォールバック
        ttk.Checkbutton(frame, text='Androidフォールバックを有効にする', 
                       variable=self.android_fallback_var).grid(
            row=current_row, column=0, columnspan=2, sticky='w', pady=10)
        current_row += 1
        
        # 字幕設定セクション
        ttk.Label(frame, text='字幕設定', font=('', 12, 'bold')).grid(
            row=current_row, column=0, sticky='w', pady=(20, 10))
        current_row += 1
        
        # 字幕言語
        ttk.Label(frame, text='字幕言語:').grid(
            row=current_row, column=0, sticky='w', pady=5)
        ttk.Entry(frame, textvariable=self.sub_lang_var, width=40).grid(
            row=current_row, column=1, sticky='w', padx=10)
        ttk.Label(frame, text='(カンマ区切り)', font=('', 8)).grid(
            row=current_row, column=2, sticky='w', padx=5)
        current_row += 1

    def _build_format_tab(self):
        frame = ttk.Frame(self.format_tab, padding=20)
        frame.grid(sticky='nsew')
        self.format_tab.grid_rowconfigure(0, weight=1)
        self.format_tab.grid_columnconfigure(0, weight=1)
        
        # フォーマット設定の表示・編集
        ttk.Label(frame, text='フォーマット別詳細設定', font=('', 12, 'bold')).grid(
            row=0, column=0, sticky='w', pady=(0, 10))
        
        # フォーマットオプションの表示
        format_text = tk.Text(frame, height=20, width=80)
        format_text.grid(row=1, column=0, sticky='nsew', pady=10)
        
        # スクロールバー
        scrollbar_fmt = ttk.Scrollbar(frame, orient="vertical", command=format_text.yview)
        scrollbar_fmt.grid(row=1, column=1, sticky='ns')
        format_text.configure(yscrollcommand=scrollbar_fmt.set)
        
        # フォーマット設定の内容を表示
        format_options = self.config_data.get('format_options', {})
        format_text.insert('1.0', json.dumps(format_options, indent=2, ensure_ascii=False))
        
        self.format_text = format_text
        
        # ボタンフレーム
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(btn_frame, text='フォーマット設定を更新', 
                  command=self.update_format_options).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='デフォルトに戻す', 
                  command=self.reset_format_options).grid(row=0, column=1, padx=5)

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

    def choose_ffmpeg(self):
        path = filedialog.askopenfilename(filetypes=[('Executable', '*.exe'), ('All files', '*.*')])
        if path:
            self.ffmpeg_var.set(path)

    def update_format_options(self):
        try:
            # テキストエリアからJSONを読み取り
            format_text_content = self.format_text.get('1.0', tk.END).strip()
            format_options = json.loads(format_text_content)
            self.config_data['format_options'] = format_options
            messagebox.showinfo('成功', 'フォーマット設定を更新しました。')
        except json.JSONDecodeError as e:
            messagebox.showerror('エラー', f'JSONの形式が正しくありません:\n{e}')
        except Exception as e:
            messagebox.showerror('エラー', f'設定の更新中にエラーが発生しました:\n{e}')

    def reset_format_options(self):
        if messagebox.askyesno('確認', 'フォーマット設定をデフォルトに戻しますか？'):
            self.format_text.delete('1.0', tk.END)
            default_format_options = DEFAULT_CONFIG['format_options']
            self.format_text.insert('1.0', json.dumps(default_format_options, indent=2, ensure_ascii=False))

    def reset_to_default(self):
        if messagebox.askyesno('確認', 'すべての設定をデフォルトに戻しますか？'):
            self.config_data = DEFAULT_CONFIG.copy()
            self._update_ui_from_config()
            messagebox.showinfo('完了', 'すべての設定をデフォルトに戻しました。')

    def _update_ui_from_config(self):
        # UI要素を設定データに基づいて更新
        self.dir_var.set(self.config_data.get('default_directory', ''))
        self.format_var.set(self.config_data.get('default_format', 'mp3'))
        self.ffmpeg_var.set(self.config_data.get('ffmpeg_path', ''))
        self.sub_dl_var.set(self.config_data.get('download_subtitles', False))
        self.sub_embed_var.set(self.config_data.get('embed_subtitles', False))
        self.makedir_var.set(self.config_data.get('makedirector', True))
        self.sub_lang_var.set(','.join(self.config_data.get('subtitle_languages', ['ja', 'en'])))
        self.info_json_var.set(self.config_data.get('write_info_json', True))
        self.thumbnail_var.set(self.config_data.get('write_thumbnail', True))
        self.max_height_var.set(str(self.config_data.get('max_height', 1080)))
        self.fallback_height_var.set(str(self.config_data.get('fallback_height', 720)))
        self.audio_quality_var.set(str(self.config_data.get('audio_quality', '192')))
        self.player_clients_var.set(','.join(self.config_data.get('player_clients', ['android', 'web', 'ios'])))
        self.skip_formats_var.set(','.join(self.config_data.get('skip_formats', ['hls'])))
        self.android_fallback_var.set(self.config_data.get('enable_android_fallback', True))
        
        # ディレクトリリストを更新
        self._refresh_directory_list()
        
        # フォーマット設定テキストを更新
        if hasattr(self, 'format_text'):
            self.format_text.delete('1.0', tk.END)
            format_options = self.config_data.get('format_options', {})
            self.format_text.insert('1.0', json.dumps(format_options, indent=2, ensure_ascii=False))

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
        try:
            # 基本設定
            self.config_data['default_directory'] = self.dir_var.get()
            self.config_data['default_format'] = self.format_var.get()
            self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
            self.config_data['download_subtitles'] = self.sub_dl_var.get()
            self.config_data['embed_subtitles'] = self.sub_embed_var.get()
            self.config_data['makedirector'] = self.makedir_var.get()
            
            # 新しい設定項目
            self.config_data['write_info_json'] = self.info_json_var.get()
            self.config_data['write_thumbnail'] = self.thumbnail_var.get()
            
            # 字幕言語（カンマ区切りの文字列をリストに変換）
            sub_langs = [lang.strip() for lang in self.sub_lang_var.get().split(',') if lang.strip()]
            self.config_data['subtitle_languages'] = sub_langs if sub_langs else ['ja', 'en']
            
            # 品質設定
            try:
                self.config_data['max_height'] = int(self.max_height_var.get())
            except ValueError:
                self.config_data['max_height'] = 1080
                
            try:
                self.config_data['fallback_height'] = int(self.fallback_height_var.get())
            except ValueError:
                self.config_data['fallback_height'] = 720
                
            self.config_data['audio_quality'] = self.audio_quality_var.get()
            
            # 高度な設定
            player_clients = [client.strip() for client in self.player_clients_var.get().split(',') if client.strip()]
            self.config_data['player_clients'] = player_clients if player_clients else ['android', 'web', 'ios']
            
            skip_formats = [fmt.strip() for fmt in self.skip_formats_var.get().split(',') if fmt.strip()]
            self.config_data['skip_formats'] = skip_formats if skip_formats else ['hls']
            
            self.config_data['enable_android_fallback'] = self.android_fallback_var.get()
            
            # フォーマット設定（既に update_format_options で更新されている）
            
            # 設定を保存
            save_config(self.config_data)
            messagebox.showinfo('保存', '設定を保存しました。')
            
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存中にエラーが発生しました:\n{e}')

    def validate_json_format(self, json_text):
        """JSONフォーマットの検証"""
        try:
            json.loads(json_text)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)

    def export_config(self):
        """設定をファイルにエクスポート"""
        file_path = filedialog.asksaveasfilename(
            title="設定をエクスポート",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config_data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo('成功', f'設定を {file_path} にエクスポートしました。')
            except Exception as e:
                messagebox.showerror('エラー', f'エクスポート中にエラーが発生しました:\n{e}')

    def import_config(self):
        """設定をファイルからインポート"""
        file_path = filedialog.askopenfilename(
            title="設定をインポート",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
                
                # インポートした設定をマージ
                for key, value in imported_config.items():
                    self.config_data[key] = value
                
                # UIを更新
                self._update_ui_from_config()
                messagebox.showinfo('成功', f'設定を {file_path} からインポートしました。')
                
            except Exception as e:
                messagebox.showerror('エラー', f'インポート中にエラーが発生しました:\n{e}')

if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()