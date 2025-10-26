import json
import os
import re
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# 設定ファイル(config.json)のパスを定義
CONFIG_FILE = Path(__file__).parent / '設定・履歴/config.json'

class ConfigGUI(tk.Tk):
    """
    設定を管理するためのGUIアプリケーションクラス。
    """
    def __init__(self):
        """
        GUIウィンドウの初期化。
        """
        super().__init__()
        self.title('設定マネージャー')
        self.geometry('1000x800')
        self.resizable(True, True)
        
        # 設定の読み込み
        if not CONFIG_FILE.exists():
            self.config_data = self._get_default_config().copy()
        else:
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                default_conf = self._get_default_config()
                for key, value in default_conf.items():
                    config.setdefault(key, value)
                
                for key in ["interactive_selection", "download_subtitles", "embed_subtitles"]:
                    config.pop(key, None)
                
                self.config_data = config
            except (json.JSONDecodeError, IOError):
                self.config_data = self._get_default_config().copy()

        self._is_updating_notion_id = False
        self._is_updating_gdrive_id = False
        self.dir_widgets = [] # ディレクトリ設定のウィジェットを保持するリスト
        self._create_vars() # Tkinter変数を初期化
        self._build_ui() # UIを構築

    def _get_default_config(self):
        """
        デフォルトの設定を生成する関数。
        初回起動時や設定ファイルが壊れている場合に使用される。
        """
        home_dir = Path.home()
        log_file_path = str(Path(__file__).parent / '設定・履歴/log.json')
        token_file_path = str(Path(__file__).parent / '設定・履歴/token.json')

        # 基本的な設定項目を辞書として定義
        base_config = {
            "video_quality": "best",
            "create_playlist_folder": True,
            "enable_logging": True,
            "log_file_path": log_file_path,
            "enable_volume_adjustment": False,
            "volume_level": 1.0,
            "enable_notion_upload": False,
            "notion_api_key": "",
            "notion_database_id": "",
            "cookie_source": "none",
            "cookie_browser": "chrome",
            "cookie_file_path": "",
            "mark_as_watched": False,
            "directories": [
                {"path": str(home_dir / "Music"), "format": "mp3"},
                {"path": str(home_dir / "Videos"), "format": "webm"},
                {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
            ],
            "default_directory_index": 1,
            "destination": "local",
            "google_drive_parent_folder_id": "",
            "google_drive_credentials_path": "",
            "google_drive_token_path": token_file_path,
        }

        # OSに応じてffmpegのデフォルトパスを設定
        if os.name == 'nt': # Windowsの場合
            base_config["ffmpeg_path"] = "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe"
            base_config["directories"]=[
                {"path": str(home_dir / "Music"), "format": "mp3"},
                {"path": str(home_dir / "Videos"), "format": "webm"},
                {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
            ]
        else: # Linuxやその他のOSの場合
            base_config["ffmpeg_path"] = "ffmpeg"
            base_config["directories"]=[
                {"path": str(home_dir / "Music"), "format": "mp3"},
                {"path": str(home_dir / "Videos"), "format": "webm"},
                {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
            ]
            
        return base_config

    def _create_vars(self):
        """
        GUIウィジェットにバインドするTkinter変数を初期化する。
        """
        self.dir_var = tk.IntVar(value=self.config_data.get('default_directory_index'))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path'))
        self.video_quality_var = tk.StringVar(value=self.config_data.get('video_quality', 'best'))
        self.create_playlist_folder_var = tk.BooleanVar(value=self.config_data.get('create_playlist_folder', True))
        self.enable_logging_var = tk.BooleanVar(value=self.config_data.get('enable_logging'))
        self.log_path_var = tk.StringVar(value=self.config_data.get('log_file_path'))
        self.enable_volume_var = tk.BooleanVar(value=self.config_data.get('enable_volume_adjustment'))
        self.volume_level_var = tk.DoubleVar(value=self.config_data.get('volume_level'))
        self.enable_notion_var = tk.BooleanVar(value=self.config_data.get('enable_notion_upload'))
        self.notion_api_key_var = tk.StringVar(value=self.config_data.get('notion_api_key'))
        self.notion_db_id_var = tk.StringVar(value=self.config_data.get('notion_database_id'))
        self.notion_db_id_var.trace_add('write', self._on_notion_db_id_change)
        self.cookie_source_var = tk.StringVar(value=self.config_data.get('cookie_source', 'none'))
        self.cookie_browser_var = tk.StringVar(value=self.config_data.get('cookie_browser'))
        self.cookie_file_path_var = tk.StringVar(value=self.config_data.get('cookie_file_path', ''))
        self.mark_as_watched_var = tk.BooleanVar(value=self.config_data.get('mark_as_watched', False))

        # Destination choice
        self.destination_var = tk.StringVar(value=self.config_data.get('destination', 'local'))

        # Google Drive settings
        self.gdrive_parent_id_var = tk.StringVar(value=self.config_data.get('google_drive_parent_folder_id', ''))
        self.gdrive_parent_id_var.trace_add('write', self._on_gdrive_folder_id_change)
        self.gdrive_credentials_path_var = tk.StringVar(value=self.config_data.get('google_drive_credentials_path', ''))

        # 設定キーとTkinter変数をマッピング
        self.settings_map = {
            'ffmpeg_path': self.ffmpeg_var,
            'video_quality': self.video_quality_var,
            'create_playlist_folder': self.create_playlist_folder_var,
            'enable_logging': self.enable_logging_var,
            'log_file_path': self.log_path_var,
            'enable_volume_adjustment': self.enable_volume_var,
            'volume_level': self.volume_level_var,
            'enable_notion_upload': self.enable_notion_var,
            'notion_api_key': self.notion_api_key_var,
            'notion_database_id': self.notion_db_id_var,
            'cookie_source': self.cookie_source_var,
            'cookie_browser': self.cookie_browser_var,
            'cookie_file_path': self.cookie_file_path_var,
            'mark_as_watched': self.mark_as_watched_var,
            'destination': self.destination_var,
            'google_drive_parent_folder_id': self.gdrive_parent_id_var,
            'google_drive_credentials_path': self.gdrive_credentials_path_var,
        }

    def _build_ui(self):
        """
        メインUIを構築する。タブ付きインターフェースを作成。
        """
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        # 上部のボタン（保存など）を作成
        self._create_top_buttons(main_frame)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=(10, 0))

        # タブ1: 一般設定
        general_tab = ttk.Frame(notebook, padding=10)
        notebook.add(general_tab, text='一般設定')
        self._create_directory_section(general_tab)
        self._create_gdrive_config_section(general_tab)

        # タブ2: ダウンロード設定
        download_tab = ttk.Frame(notebook, padding=10)
        notebook.add(download_tab, text='ダウンロード設定')
        self._create_other_settings_section(download_tab)

        # タブ3: 連携・その他
        advanced_tab = ttk.Frame(notebook, padding=10)
        notebook.add(advanced_tab, text='連携・その他')
        self._create_cookie_config_section(advanced_tab)
        self._create_log_config_section(advanced_tab)
        self._create_notion_config_section(advanced_tab)

        # 各コントロールの初期状態を更新
        self._update_log_controls()
        self._update_volume_controls()
        self._update_notion_controls()
        self._update_cookie_controls()
        self._update_destination_views()

    def _create_directory_section(self, parent):
        """
        ダウンロード先ディレクトリ設定セクションを作成する。
        """
        # Destination selection
        dest_frame = ttk.LabelFrame(parent, text='保存先', padding=5)
        dest_frame.pack(fill='x', pady=(0, 10))
        ttk.Radiobutton(dest_frame, text='ローカル保存', variable=self.destination_var, value='local', command=self._update_destination_views).pack(side='left', padx=5)
        ttk.Radiobutton(dest_frame, text='Google Driveへアップロード', variable=self.destination_var, value='gdrive', command=self._update_destination_views).pack(side='left', padx=5)

        self.local_dir_frame = ttk.LabelFrame(parent, text='ダウンロード先ディレクトリ', padding=5)
        self.local_dir_frame.pack(fill='both', expand=True, pady=(0, 10))
        btn_frame = ttk.Frame(self.local_dir_frame)
        btn_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(btn_frame, text='ディレクトリを追加', command=self.add_directory).pack(side='left')
        ttk.Label(btn_frame, text='※ディレクトリを追加後、パスを設定してください').pack(side='left', padx=(10, 0))

        # スクロール可能なディレクトリリスト領域
        canvas_frame = ttk.Frame(self.local_dir_frame)
        canvas_frame.pack(fill='both', expand=True)
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._build_directory_list()

    def _create_other_settings_section(self, parent):
        """
        ffmpegパス、画質、音量調整などの設定セクションを作成する。
        """
        other_frame = ttk.LabelFrame(parent, text="その他の設定", padding=5)
        other_frame.pack(fill='x', pady=(0, 10))

        # ffmpegパス設定
        ffmpeg_frame = ttk.Frame(other_frame)
        ffmpeg_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(ffmpeg_frame, text='ffmpegパス:').pack(anchor='w')
        ffmpeg_entry_frame = ttk.Frame(ffmpeg_frame)
        ffmpeg_entry_frame.pack(fill='x', pady=(2, 0))
        ttk.Entry(ffmpeg_entry_frame, textvariable=self.ffmpeg_var).pack(side='left', fill='x', expand=True)
        ttk.Button(ffmpeg_entry_frame, text='選択', command=self.choose_ffmpeg).pack(side='right', padx=(5, 0))

        # 動画画質設定
        quality_frame = ttk.Frame(other_frame)
        quality_frame.pack(fill='x', pady=(5, 5))
        ttk.Label(quality_frame, text='動画の画質:').pack(side='left', anchor='w')
        quality_options = ['best','2160' ,'1440','1080', '720', '480', '360']
        ttk.Combobox(quality_frame, textvariable=self.video_quality_var, values=quality_options).pack(side='left', padx=5)
        ttk.Label(quality_frame, text='("best", "1080"など。指定解像度以下の最大画質)').pack(side='left', anchor='w')

        # プレイリストのディレクトリ作成設定
        ttk.Checkbutton(other_frame, text='プレイリストの場合、ディレクトリを作成する', variable=self.create_playlist_folder_var).pack(anchor='w', pady=2)

        # 音量調整設定
        self.volume_check = ttk.Checkbutton(other_frame, text='音量を調整する', variable=self.enable_volume_var, command=self._update_volume_controls)
        self.volume_check.pack(anchor='w', pady=(10, 2))
        self.volume_frame = ttk.Frame(other_frame)
        self.volume_frame.pack(fill='x', padx=20, pady=(0, 5))
        self.volume_label_var = tk.StringVar(value=f"{self.volume_level_var.get():.2f}")
        self.volume_scale = ttk.Scale(self.volume_frame, from_=0.0, to=2.0, orient='horizontal', variable=self.volume_level_var, command=lambda s: self.volume_label_var.set(f"{float(s):.2f}"))
        self.volume_scale.pack(side='left', fill='x', expand=True)
        self.volume_label = ttk.Label(self.volume_frame, textvariable=self.volume_label_var, width=5)
        self.volume_label.pack(side='right')

    def _create_cookie_config_section(self, parent):
        """
        Cookie設定セクションを作成する。
        """
        cookie_config_frame = ttk.LabelFrame(parent, text="Cookie設定", padding=5)
        cookie_config_frame.pack(fill='x', pady=(0, 10))

        # Radio buttons for selection
        ttk.Radiobutton(cookie_config_frame, text='使用しない', variable=self.cookie_source_var, value='none', command=self._update_cookie_controls).pack(anchor='w')
        ttk.Radiobutton(cookie_config_frame, text='ブラウザから自動取得', variable=self.cookie_source_var, value='browser', command=self._update_cookie_controls).pack(anchor='w')
        
        # --- Browser selection frame ---
        self.cookie_browser_frame = ttk.Frame(cookie_config_frame)
        self.cookie_browser_frame.pack(fill='x', padx=20, pady=2)
        self.cookie_browser_label = ttk.Label(self.cookie_browser_frame, text='使用するブラウザ:')
        self.cookie_browser_label.pack(side='left', anchor='w')
        browser_options = ['chrome', 'firefox', 'brave', 'edge', 'opera', 'safari', 'vivaldi']
        self.cookie_browser_combo = ttk.Combobox(self.cookie_browser_frame, textvariable=self.cookie_browser_var, values=browser_options, state='readonly')
        self.cookie_browser_combo.pack(side='left', padx=5)

        ttk.Radiobutton(cookie_config_frame, text='Cookieファイルを使用する', variable=self.cookie_source_var, value='file', command=self._update_cookie_controls).pack(anchor='w')

        # --- Cookie file selection frame ---
        self.cookie_file_frame = ttk.Frame(cookie_config_frame)
        self.cookie_file_frame.pack(fill='x', padx=20, pady=2)
        self.cookie_file_label = ttk.Label(self.cookie_file_frame, text='Cookieファイルパス:')
        self.cookie_file_label.pack(anchor='w')
        file_entry_frame = ttk.Frame(self.cookie_file_frame)
        file_entry_frame.pack(fill='x', pady=(2, 0))
        self.cookie_file_entry = ttk.Entry(file_entry_frame, textvariable=self.cookie_file_path_var)
        self.cookie_file_entry.pack(side='left', fill='x', expand=True)
        self.cookie_file_btn = ttk.Button(file_entry_frame, text='選択', command=self.choose_cookie_file)
        self.cookie_file_btn.pack(side='right', padx=(5, 0))

        # --- Mark as watched checkbox ---
        self.mark_as_watched_check = ttk.Checkbutton(cookie_config_frame, text='YouTubeの視聴履歴に追加する', variable=self.mark_as_watched_var)
        self.mark_as_watched_check.pack(anchor='w', pady=(10, 0))

    def _create_log_config_section(self, parent):
        """
        ログ設定セクションを作成する。
        """
        log_config_frame = ttk.LabelFrame(parent, text="ログ設定", padding=5)
        log_config_frame.pack(fill='x', pady=(0, 10))
        ttk.Checkbutton(log_config_frame, text='ログ機能を有効にする', variable=self.enable_logging_var, command=self._update_log_controls).pack(anchor='w')
        self.log_path_frame = ttk.Frame(log_config_frame)
        self.log_path_frame.pack(fill='x', pady=(5, 0))
        self.log_path_label = ttk.Label(self.log_path_frame, text='ログファイルパス:')
        self.log_path_label.pack(anchor='w')
        log_entry_frame = ttk.Frame(self.log_path_frame)
        log_entry_frame.pack(fill='x', pady=(2, 0))
        self.log_path_entry = ttk.Entry(log_entry_frame, textvariable=self.log_path_var)
        self.log_path_entry.pack(side='left', fill='x', expand=True)
        self.log_path_btn = ttk.Button(log_entry_frame, text='選択', command=self.choose_log_file)
        self.log_path_btn.pack(side='right', padx=(5, 0))

    def _create_notion_config_section(self, parent):
        """
        Notion連携設定セクションを作成する。
        """
        notion_config_frame = ttk.LabelFrame(parent, text="Notion連携設定", padding=5)
        notion_config_frame.pack(fill='x', pady=(0, 10))
        ttk.Checkbutton(notion_config_frame, text='Notionへのアップロードを有効にする', variable=self.enable_notion_var, command=self._update_notion_controls).pack(anchor='w')
        
        self.notion_widgets_frame = ttk.Frame(notion_config_frame)
        self.notion_widgets_frame.pack(fill='x', padx=20, pady=5)

        self.notion_api_key_label = ttk.Label(self.notion_widgets_frame, text='Notion APIキー:')
        self.notion_api_key_label.pack(anchor='w')
        self.notion_api_key_entry = ttk.Entry(self.notion_widgets_frame, textvariable=self.notion_api_key_var, show='*')
        self.notion_api_key_entry.pack(fill='x', pady=(0, 5))

        self.notion_db_id_label = ttk.Label(self.notion_widgets_frame, text='NotionデータベースのURLまたはID（IDとして貼り付けられます。）:')
        self.notion_db_id_label.pack(anchor='w')
        self.notion_db_id_entry = ttk.Entry(self.notion_widgets_frame, textvariable=self.notion_db_id_var)
        self.notion_db_id_entry.pack(fill='x')

    def _on_notion_db_id_change(self, *args):
        if hasattr(self, '_is_updating_notion_id') and self._is_updating_notion_id:
            return
        
        current_value = self.notion_db_id_var.get()
        
        if 'notion.so' in current_value and '/' in current_value:
            try:
                match = re.search(r'([a-fA-F0-9]{32})', current_value)
                if match:
                    db_id = match.group(1)
                    if db_id != current_value:
                        self._is_updating_notion_id = True
                        self.notion_db_id_var.set(db_id)
                        self._is_updating_notion_id = False
            except Exception:
                pass

    def _on_gdrive_folder_id_change(self, *args):
        if hasattr(self, '_is_updating_gdrive_id') and self._is_updating_gdrive_id:
            return
        
        current_value = self.gdrive_parent_id_var.get()
        
        if 'drive.google.com' in current_value and '/folders/' in current_value:
            try:
                match = re.search(r'/folders/([a-zA-Z0-9_-]+)', current_value)
                if match:
                    folder_id = match.group(1)
                    if folder_id != current_value:
                        self._is_updating_gdrive_id = True
                        self.gdrive_parent_id_var.set(folder_id)
                        self._is_updating_gdrive_id = False
            except Exception:
                pass

    def _create_top_buttons(self, parent):
        """
        ウィンドウ上部の「保存して終了」「設定ファイルを開く」ボタンを作成する。
        """
        top_btn_frame = ttk.Frame(parent)
        top_btn_frame.pack(fill='x', pady=(0, 10))
        ttk.Button(top_btn_frame, text='保存して終了', command=self.on_save_and_exit).pack(side='left', padx=(0, 5))
        ttk.Button(top_btn_frame, text='設定ファイルを開く', command=self.open_config).pack(side='left', padx=5)

    def _update_volume_controls(self):
        """
        音量調整が有効かどうかに応じて、関連ウィジェットの有効/無効を切り替える。
        """
        state = 'normal' if self.enable_volume_var.get() else 'disabled'
        self.volume_scale.config(state=state)
        self.volume_label.config(foreground='black' if state == 'normal' else 'grey')

    def _update_log_controls(self):
        """
        ログ機能が有効かどうかに応じて、関連ウィジェットの有効/無効を切り替える。
        """
        state = 'normal' if self.enable_logging_var.get() else 'disabled'
        for widget in [self.log_path_entry, self.log_path_btn, self.log_path_label]:
            widget.config(state=state) if not isinstance(widget, ttk.Label) else widget.config(foreground='black' if state == 'normal' else 'gray')

    def _update_notion_controls(self):
        """
        Notion連携が有効かどうかに応じて、関連ウィジェットの有効/無効を切り替える。
        """
        state = 'normal' if self.enable_notion_var.get() else 'disabled'
        for widget in [self.notion_api_key_label, self.notion_api_key_entry, self.notion_db_id_label, self.notion_db_id_entry]:
            widget.config(state=state) if not isinstance(widget, ttk.Label) else widget.config(foreground='black' if state == 'normal' else 'gray')

    def _update_cookie_controls(self):
        """
        Cookie設定の選択に応じてUIの有効/無効を切り替える。
        """
        source = self.cookie_source_var.get()
        
        # Browser controls
        browser_state = 'readonly' if source == 'browser' else 'disabled'
        self.cookie_browser_combo.config(state=browser_state)
        self.cookie_browser_label.config(foreground='black' if source == 'browser' else 'gray')

        # File controls
        file_state = 'normal' if source == 'file' else 'disabled'
        self.cookie_file_entry.config(state=file_state)
        self.cookie_file_btn.config(state=file_state)
        self.cookie_file_label.config(foreground='black' if source == 'file' else 'gray')

        # Mark as watched control
        watched_state = 'normal' if source in ['browser', 'file'] else 'disabled'
        self.mark_as_watched_check.config(state=watched_state)

    def _build_directory_list(self):
        """
        設定データに基づいてディレクトリリストのUIを再構築する。
        """
        # 既存のウィジェットをすべて破棄
        for widgets in self.dir_widgets:
            widgets['frame'].destroy()
        self.dir_widgets.clear()
        # 設定データから新しいウィジェットを作成
        for i, dir_info in enumerate(self.config_data['directories']):
            self._create_directory_row(i, dir_info)
        self.scrollable_frame.update_idletasks()

    def _create_directory_row(self, index, dir_info):
        """
        ディレクトリリストの各行のウィジェットを作成する。
        """
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill='x', pady=2, padx=5)
        widgets = {'frame': row_frame}

        # デフォルト選択用のラジオボタン
        widgets['radio'] = ttk.Radiobutton(row_frame, text=f"候補{index + 1}", variable=self.dir_var, value=index)
        widgets['radio'].pack(side='left')

        # パス入力欄
        widgets['path_var'] = tk.StringVar(value=dir_info['path'])
        widgets['path_entry'] = ttk.Entry(row_frame, textvariable=widgets['path_var'], width=40)
        widgets['path_entry'].pack(side='left', fill='x', expand=True, padx=(5, 0))

        # フォーマット選択コンボボックス
        widgets['format_var'] = tk.StringVar(value=dir_info['format'])
        widgets['format_combo'] = ttk.Combobox(row_frame, textvariable=widgets['format_var'], values=['mp3', 'mp4', 'webm', 'wav', 'flac'], width=8, state='readonly')
        widgets['format_combo'].pack(side='right', padx=(5, 0))

        # パス選択ボタン
        widgets['select_btn'] = ttk.Button(row_frame, text='選択', command=lambda idx=index: self.change_dir(idx))
        widgets['select_btn'].pack(side='right', padx=(5, 0))

        # 削除ボタン
        widgets['delete_btn'] = ttk.Button(row_frame, text='削除', command=lambda idx=index: self.delete_directory(idx))
        widgets['delete_btn'].pack(side='right', padx=(5, 0))
        # ディレクトリが1つしかない場合は削除不可にする
        if len(self.config_data['directories']) <= 1:
            widgets['delete_btn'].config(state='disabled')
        
        self.dir_widgets.append(widgets)

    def add_directory(self):
        """
        新しいディレクトリ候補を追加する。
        """
        self.config_data['directories'].append({"path": "", "format": "mp3"})
        self._build_directory_list()
        messagebox.showinfo('追加完了', f'新しいディレクトリ候補{len(self.config_data["directories"])}を追加しました。\nパスを設定してください。')

    def delete_directory(self, index):
        """
        指定されたインデックスのディレクトリ候補を削除する。
        """
        if len(self.config_data['directories']) <= 1:
            return messagebox.showwarning('警告', '最低1つのディレクトリは必要です。')
        
        dir_path = self.dir_widgets[index]['path_var'].get() or f"候補{index + 1}"
        if messagebox.askyesno('確認', f'"{dir_path}"を削除しますか？'):
            self.config_data['directories'].pop(index)
            # デフォルト選択が範囲外になった場合は調整
            if self.dir_var.get() >= len(self.config_data['directories']):
                self.dir_var.set(len(self.config_data['directories']) - 1)
            self._build_directory_list()

    def change_dir(self, index):
        """
        ディレクトリ選択ダイアログを開き、選択されたパスを設定する。
        """
        if new_path := filedialog.askdirectory(title=f'候補{index + 1}のディレクトリを選択'):
            self.dir_widgets[index]['path_var'].set(new_path)

    def choose_ffmpeg(self):
        """
        ffmpeg実行ファイルの選択ダイアログを開く。
        """
        if path := filedialog.askopenfilename(title='ffmpegの実行ファイルを選択', filetypes=[('Executable', '*.exe'), ('All files', '*.*')]):
            self.ffmpeg_var.set(path)

    def choose_log_file(self):
        """
        ログファイルの保存先選択ダイアログを開く。
        """
        if path := filedialog.asksaveasfilename(title='ログファイルの保存先を選択', defaultextension='.json', filetypes=[('JSON files', '*.json'), ('All files', '*.*')]):
            self.log_path_var.set(path)

    def choose_cookie_file(self):
        """
        Cookieファイルの選択ダイアログを開く。
        """
        if path := filedialog.askopenfilename(title='Cookieファイルを選択', filetypes=[('Text files', '*.txt'), ('All files', '*.*')]):
            self.cookie_file_path_var.set(path)

    def _create_gdrive_config_section(self, parent):
        """
        Google Drive連携設定セクションを作成する。
        """
        self.gdrive_frame = ttk.LabelFrame(parent, text="Google Drive連携設定", padding=5)
        self.gdrive_frame.pack(fill='x', pady=(0, 10))
        
        self.gdrive_widgets_frame = ttk.Frame(self.gdrive_frame)
        self.gdrive_widgets_frame.pack(fill='x', padx=20, pady=5)

        self.gdrive_parent_id_label = ttk.Label(self.gdrive_widgets_frame, text='親フォルダID:')
        self.gdrive_parent_id_label.pack(anchor='w')
        self.gdrive_parent_id_entry = ttk.Entry(self.gdrive_widgets_frame, textvariable=self.gdrive_parent_id_var)
        self.gdrive_parent_id_entry.pack(fill='x', pady=(0, 5))

        self.gdrive_credentials_label = ttk.Label(self.gdrive_widgets_frame, text='認証情報ファイル (credentials.json):')
        self.gdrive_credentials_label.pack(anchor='w')
        cred_frame = ttk.Frame(self.gdrive_widgets_frame)
        cred_frame.pack(fill='x', pady=(0, 5))
        self.gdrive_credentials_entry = ttk.Entry(cred_frame, textvariable=self.gdrive_credentials_path_var)
        self.gdrive_credentials_entry.pack(side='left', fill='x', expand=True)
        self.gdrive_credentials_btn = ttk.Button(cred_frame, text='選択', command=self.choose_gdrive_credentials)
        self.gdrive_credentials_btn.pack(side='right', padx=(5, 0))

    def _update_destination_views(self):
        """
        保存先の選択に応じて、ローカル用とGoogle Drive用の設定UIを切り替えて表示する。
        """
        if self.destination_var.get() == 'gdrive':
            self.local_dir_frame.pack_forget()
            self.gdrive_frame.pack(fill='x', pady=(0, 10))
        else:
            self.gdrive_frame.pack_forget()
            self.local_dir_frame.pack(fill='both', expand=True, pady=(0, 10))

    def choose_gdrive_credentials(self):
        """
        認証情報ファイル(credentials.json)の選択ダイアログを開く。
        """
        if path := filedialog.askopenfilename(title='認証情報ファイルを選択', filetypes=[('JSON files', '*.json'), ('All files', '*.*')]):
            self.gdrive_credentials_path_var.set(path)

    def open_config(self):
        """
        設定ファイル(config.json)を開く。
        """
        try:
            if sys.platform == 'win32':
                os.startfile(CONFIG_FILE)
            elif sys.platform == 'darwin':
                subprocess.run(['open', CONFIG_FILE], check=True)
            else:
                subprocess.run(['xdg-open', CONFIG_FILE], check=True)
        except Exception as e:
            messagebox.showerror('エラー', f'パスを開けませんでした: {e}\nパス: {CONFIG_FILE}')

    def on_save(self):
        """
        現在のGUIの状態を設定データに反映し、ファイルに保存する。
        """
        # パスが空でないディレクトリ情報のみを収集
        directories = [d for w in self.dir_widgets if (d := {"path": w['path_var'].get().strip(), "format": w['format_var'].get()})['path']]
        if not directories:
            messagebox.showwarning('警告', '最低1つのディレクトリを設定してください。')
            return False
        
        # ログ機能が有効なのにパスが空の場合に警告
        if self.enable_logging_var.get() and not self.log_path_var.get().strip():
            if not messagebox.askyesno('確認', 'ログ機能が有効ですが、ログファイルパスが設定されていません。\nこのまま保存しますか？'):
                return False
        
        # 設定データを更新
        self.config_data['directories'] = directories
        self.config_data['default_directory_index'] = min(self.dir_var.get(), len(directories) - 1)
        for key, var in self.settings_map.items():
            value = var.get()
            if isinstance(var, tk.DoubleVar): value = round(value, 2) # DoubleVarは丸める
            self.config_data[key] = value
        
        try:
            # 設定ファイルを保存する
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                # JSONを整形して書き込む (indent=4, ensure_ascii=False)
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存に失敗しました: {e}')
            return False

    def on_save_and_exit(self):
        """
        設定を保存してGUIを閉じる。
        """
        if self.on_save():
            self.destroy()

if __name__ == '__main__':
    # アプリケーションの実行
    app = ConfigGUI()
    app.mainloop()