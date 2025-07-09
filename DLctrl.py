import json  
import os
import sys
import subprocess  # システムコマンドを実行するためのモジュール
import tkinter as tk  
from tkinter import ttk, filedialog, messagebox  # GUI用のウィジェットやダイアログ
from pathlib import Path  # ファイルパス操作用

# 設定ファイルのパスを生成（現在のファイルと同じディレクトリに配置）
CONFIG_FILE = Path(__file__).parent / '設定・履歴/config.json'

# OSに応じたデフォルト設定を生成する関数
def get_default_config():
    # 共通のログファイルパス
    log_file_path = str(Path(__file__).parent / '設定・履歴/log.json')
    home_dir = Path.home()

    # Windowsの場合
    if os.name == 'nt':
        return {
            "ffmpeg_path": "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe",
            "download_subtitles": False,
            "embed_subtitles": False,
            "mkdir_list": True,
            "directories": [
                {"path": str(home_dir / "Music"), "format": "mp3"},
                {"path": str(home_dir / "Videos"), "format": "webm"},
                {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
            ],
            "default_directory_index": 1,
            "makedirector": True,
            "interactive_selection": False,
            "log_file_path": log_file_path,
            "enable_logging": True,
            "enable_volume_adjustment": False,
            "volume_level": 1.0
        }
    # Linux やその他のOSの場合
    else:
        return {
            "ffmpeg_path": "ffmpeg",  # PATHに通っていることを期待
            "download_subtitles": False,
            "embed_subtitles": False,
            "mkdir_list": True,
            "directories": [
                {"path": str(home_dir / "Music"), "format": "mp3"},
                {"path": str(home_dir / "Videos"), "format": "webm"},
                {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
            ],
            "default_directory_index": 1,
            "makedirector": True,
            "interactive_selection": False,
            "log_file_path": log_file_path,
            "enable_logging": True,
            "enable_volume_adjustment": False,
            "volume_level": 1.0
        }

# 設定ファイルを読み込む関数
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            # 設定ファイルが壊れている場合はデフォルト設定を返す
            return get_default_config().copy()

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
        
        # 新しいキーが存在しない場合にデフォルト値を追加
        default_conf = get_default_config()
        for key, value in default_conf.items():
            config.setdefault(key, value)
        
        return config
    return get_default_config().copy()

# 設定ファイルに設定情報を書き込む関数
def save_config(config):
    # ディレクトリが存在しない場合は作成
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# ConfigGUIクラス: 設定画面のためのメインウィンドウクラス
class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('設定マネージャー')
        self.geometry('1000x1100')  # ウィンドウの初期サイズを少し大きく設定
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
        self.enable_logging_var = tk.BooleanVar(value=self.config_data.get('enable_logging', True))
        self.log_path_var = tk.StringVar(value=self.config_data.get('log_file_path', ''))
        self.enable_volume_var = tk.BooleanVar(value=self.config_data.get('enable_volume_adjustment', False))
        self.volume_level_var = tk.DoubleVar(value=self.config_data.get('volume_level', 1.0))

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

        # 音量調整の設定
        self.volume_check = ttk.Checkbutton(
            other_frame,
            text='音量を調整する',
            variable=self.enable_volume_var,
            command=self._update_volume_controls
        )
        self.volume_check.pack(anchor='w', pady=(10, 2))

        self.volume_frame = ttk.Frame(other_frame)
        self.volume_frame.pack(fill='x', padx=20, pady=(0, 5))

        self.volume_label_var = tk.StringVar(value=f"{self.volume_level_var.get():.2f}")
        
        self.volume_scale = ttk.Scale(
            self.volume_frame,
            from_=0.0,
            to=2.0,
            orient='horizontal',
            variable=self.volume_level_var,
            command=lambda s: self.volume_label_var.set(f"{float(s):.2f}")
        )
        self.volume_scale.pack(side='left', fill='x', expand=True)

        self.volume_label = ttk.Label(self.volume_frame, textvariable=self.volume_label_var, width=5)
        self.volume_label.pack(side='right')

        # ログ設定セクション
        log_config_frame = ttk.LabelFrame(main_frame, text="ログ設定", padding=5)
        log_config_frame.pack(fill='x', pady=(0, 10))

        # ログ有効/無効の設定
        log_enable_frame = ttk.Frame(log_config_frame)
        log_enable_frame.pack(fill='x', pady=(0, 5))
        
        self.log_checkbox = ttk.Checkbutton(
            log_enable_frame, 
            text='ログ機能を有効にする', 
            variable=self.enable_logging_var,
            command=self._update_log_controls
        )
        self.log_checkbox.pack(anchor='w')

        # ログファイルパス設定
        self.log_path_frame = ttk.Frame(log_config_frame)
        self.log_path_frame.pack(fill='x', pady=(5, 0))
        ttk.Label(self.log_path_frame, text='ログファイルパス:').pack(anchor='w')
        
        log_entry_frame = ttk.Frame(self.log_path_frame)
        log_entry_frame.pack(fill='x', pady=(2, 0))
        self.log_path_entry = ttk.Entry(log_entry_frame, textvariable=self.log_path_var)
        self.log_path_entry.pack(side='left', fill='x', expand=True)
        self.log_path_btn = ttk.Button(log_entry_frame, text='選択', command=self.choose_log_file)
        self.log_path_btn.pack(side='right', padx=(5, 0))

        # ログ管理セクション
        log_section = ttk.LabelFrame(main_frame, text="ログ管理", padding=5)
        log_section.pack(fill='x', pady=(0, 10))
        
        log_btn_frame = ttk.Frame(log_section)
        log_btn_frame.pack(fill='x')
        
        self.open_log_btn = ttk.Button(log_btn_frame, text='ログファイルを開く', command=self.open_log_file)
        self.open_log_btn.pack(side='left', padx=(0, 5))
        self.open_folder_btn = ttk.Button(log_btn_frame, text='ログフォルダを開く', command=self.open_log_folder)
        self.open_folder_btn.pack(side='left', padx=(0, 5))
        self.clear_log_btn = ttk.Button(log_btn_frame, text='ログをクリア', command=self.clear_log)
        self.clear_log_btn.pack(side='left', padx=(0, 5))

        # ボタンフレーム
        bottom_btn_frame = ttk.Frame(main_frame)
        bottom_btn_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(bottom_btn_frame, text='保存して終了', command=self.on_save_and_exit).pack(side='left', padx=(0, 5))
        ttk.Button(bottom_btn_frame, text='設定ファイルを開く', command=self.open_config).pack(side='left', padx=5)

        # 初期状態でUIコントロールの有効/無効を反映
        self._update_log_controls()
        self._update_volume_controls()
        self._update_log_management_buttons()

    def _update_volume_controls(self):
        """音量調整コントロールの有効/無効を更新"""
        state = 'normal' if self.enable_volume_var.get() else 'disabled'
        self.volume_scale.config(state=state)
        self.volume_label.config(foreground='black' if state == 'normal' else 'grey')

    def _update_log_controls(self):
        """ログ設定コントロールの有効/無効を更新"""
        is_enabled = self.enable_logging_var.get()
        
        # ログファイルパス関連のコントロール
        state = 'normal' if is_enabled else 'disabled'
        self.log_path_entry.config(state=state)
        self.log_path_btn.config(state=state)
        
        # フレーム内のラベルの色も変更
        for widget in self.log_path_frame.winfo_children():
            if isinstance(widget, ttk.Label):
                widget.config(foreground='black' if is_enabled else 'gray')
        
        self._update_log_management_buttons()

    def _update_log_management_buttons(self):
        """ログ管理ボタンの有効/無効を更新"""
        is_enabled = self.enable_logging_var.get()
        state = 'normal' if is_enabled else 'disabled'
        
        self.open_log_btn.config(state=state)
        self.open_folder_btn.config(state=state)
        self.clear_log_btn.config(state=state)

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

        # 削除ボタン
        delete_btn = ttk.Button(
            row_frame,
            text='削除',
            command=lambda idx=index: self.delete_directory(idx)
        )
        delete_btn.pack(side='right', padx=(5, 0))
        # 1個しかない場合は無効化
        if len(self.config_data['directories']) <= 1:
            delete_btn.config(state='disabled')

        # ウィジェットを保存
        widgets = {
            'frame': row_frame, 'radio': radio, 'path_var': path_var,
            'path_entry': path_entry, 'format_var': format_var,
            'format_combo': format_combo, 'select_btn': select_btn,
            'delete_btn': delete_btn
        }
        self.dir_widgets.append(widgets)

    def add_directory(self):
        # 新しいディレクトリを追加
        new_dir = {"path": "", "format": "mp3"}
        self.config_data['directories'].append(new_dir)
        self._build_directory_list()
        
        messagebox.showinfo('追加完了', f'新しいディレクトリ候補{len(self.config_data["directories"])}を追加しました.\nパスを設定してください。')

    def delete_directory(self, index):
        if len(self.config_data['directories']) <= 1:
            messagebox.showwarning('警告', '最低1つのディレクトリは必要です。')
            return
        
        dir_path = self.config_data['directories'][index]['path']
        dir_name = dir_path if dir_path else f"候補{index + 1}"
        
        if messagebox.askyesno('確認', f'"{dir_name}"を削除しますか？'):
            self.config_data['directories'].pop(index)
            
            current_index = self.dir_var.get()
            if current_index == index:
                self.dir_var.set(0)
            elif current_index > index:
                self.dir_var.set(current_index - 1)
            
            self._build_directory_list()

    def change_dir(self, index):
        new_path = filedialog.askdirectory(
            title=f'候補{index + 1}のディレクトリを選択'
        )
        if new_path:
            self.dir_widgets[index]['path_var'].set(new_path)

    def choose_ffmpeg(self):
        path = filedialog.askopenfilename(
            title='ffmpegの実行ファイルを選択',
            filetypes=[('Executable', '*.exe'), ('All files', '*.*')]
        )
        if path:
            self.ffmpeg_var.set(path)

    def choose_log_file(self):
        path = filedialog.asksaveasfilename(
            title='ログファイルの保存先を選択',
            defaultextension='.json',
            filetypes=[('JSON files', '*.json'), ('All files', '*.*')]
        )
        if path:
            self.log_path_var.set(path)

    def _open_path(self, path):
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path], check=True)
            else:
                subprocess.run(['xdg-open', path], check=True)
        except Exception as e:
            messagebox.showerror('エラー', f'パスを開けませんでした: {e}\nパス: {path}')

    def open_log_file(self):
        if not self.enable_logging_var.get():
            messagebox.showinfo('情報', 'ログ機能が無効になっています。')
            return
            
        log_path = self.log_path_var.get()
        if not log_path:
            messagebox.showwarning('警告', 'ログファイルパスが設定されていません。')
            return
        
        if not os.path.exists(log_path):
            messagebox.showinfo('情報', 'ログファイルがまだ作成されていません。\nダウンロードを実行するとログファイルが作成されます。')
            return
        
        self._open_path(log_path)

    def open_log_folder(self):
        if not self.enable_logging_var.get():
            messagebox.showinfo('情報', 'ログ機能が無効になっています。')
            return
            
        log_path = self.log_path_var.get()
        if not log_path:
            messagebox.showwarning('警告', 'ログファイルパスが設定されていません。')
            return
        
        log_dir = os.path.dirname(os.path.abspath(log_path))
        if not os.path.exists(log_dir):
            if messagebox.askyesno('確認', f'ログディレクトリが存在しません。\n作成しますか？\n\n{log_dir}'):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception as e:
                    messagebox.showerror('エラー', f'ディレクトリの作成に失敗しました: {e}')
                    return
            else:
                return
        
        self._open_path(log_dir)

    def clear_log(self):
        if not self.enable_logging_var.get():
            messagebox.showinfo('情報', 'ログ機能が無効になっています。')
            return
            
        log_path = self.log_path_var.get()
        if not log_path:
            messagebox.showwarning('警告', 'ログファイルパスが設定されていません。')
            return
        
        if not os.path.exists(log_path):
            messagebox.showinfo('情報', 'ログファイルが存在しないため、クリアする必要がありません。')
            return
        
        if messagebox.askyesno('確認', 'ログファイルをクリア（削除）しますか？\nこの操作は元に戻せません。'):
            try:
                os.remove(log_path)
                messagebox.showinfo('完了', 'ログファイルをクリアしました。')
            except Exception as e:
                messagebox.showerror('エラー', f'ログファイルのクリアに失敗しました: {e}')

    def open_config(self):
        self._open_path(str(CONFIG_FILE))

    def on_save(self):
        directories = []
        for widgets in self.dir_widgets:
            path = widgets['path_var'].get().strip()
            format_val = widgets['format_var'].get()
            if path:
                directories.append({"path": path, "format": format_val})
        
        if not directories:
            messagebox.showwarning('警告', '最低1つのディレクトリを設定してください。')
            return False
        
        if self.enable_logging_var.get() and not self.log_path_var.get().strip():
            if not messagebox.askyesno('確認', 'ログ機能が有効ですが、ログファイルパスが設定されていません。\nこのまま保存しますか？'):
                return False
        
        self.config_data['directories'] = directories
        self.config_data['default_directory_index'] = min(self.dir_var.get(), len(directories) - 1)
        self.config_data['interactive_selection'] = self.interactive_var.get()
        self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
        self.config_data['download_subtitles'] = self.sub_dl_var.get()
        self.config_data['embed_subtitles'] = self.sub_embed_var.get()
        self.config_data['makedirector'] = self.makedir_var.get()
        self.config_data['enable_logging'] = self.enable_logging_var.get()
        self.config_data['log_file_path'] = self.log_path_var.get()
        self.config_data['enable_volume_adjustment'] = self.enable_volume_var.get()
        self.config_data['volume_level'] = round(self.volume_level_var.get(), 2)
        
        try:
            save_config(self.config_data)
            return True
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存に失敗しました: {e}')
            return False

    def on_save_and_exit(self):
        if self.on_save():
            self.destroy()

# メイン処理
if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()
