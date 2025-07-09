import json
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / '設定・履歴/config.json'

def get_default_config():
    home_dir = Path.home()
    log_file_path = str(Path(__file__).parent / '設定・履歴/log.json')
    
    base_config = {
        "download_subtitles": False,
        "embed_subtitles": False,
        "mkdir_list": True,
        "makedirector": True,
        "interactive_selection": False,
        "enable_logging": True,
        "log_file_path": log_file_path,
        "enable_volume_adjustment": False,
        "volume_level": 1.0,
        "directories": [
            {"path": str(home_dir / "Music"), "format": "mp3"},
            {"path": str(home_dir / "Videos"), "format": "webm"},
            {"path": str(home_dir / "Documents" / "Podcasts"), "format": "webm"},
        ],
        "default_directory_index": 1,
    }
    
    if os.name == 'nt':
        base_config["ffmpeg_path"] = "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe"
    else: # Linux or other
        base_config["ffmpeg_path"] = "ffmpeg"
        
    return base_config

def load_config():
    if not CONFIG_FILE.exists():
        return get_default_config().copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return get_default_config().copy()

    # Migrate from old format if necessary
    if 'directory1' in config:
        directories = []
        for i in range(1, 4):
            if dir_key := f'directory{i}' in config:
                directories.append({"path": config[dir_key], "format": config.get('default_format', 'mp3')})
        config['directories'] = directories
        config['default_directory_index'] = 0
        for key in ['directory1', 'directory2', 'directory3', 'default_directory', 'default_format']:
            config.pop(key, None)
    
    # Ensure all keys are present
    default_conf = get_default_config()
    for key, value in default_conf.items():
        config.setdefault(key, value)
    
    return config

def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('設定マネージャー')
        self.geometry('1000x1100')
        self.resizable(True, True)
        self.config_data = load_config()
        self.dir_widgets = []
        self._create_vars()
        self._build_ui()

    def _create_vars(self):
        self.dir_var = tk.IntVar(value=self.config_data.get('default_directory_index'))
        self.interactive_var = tk.BooleanVar(value=self.config_data.get('interactive_selection'))
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path'))
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles'))
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles'))
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('makedirector'))
        self.enable_logging_var = tk.BooleanVar(value=self.config_data.get('enable_logging'))
        self.log_path_var = tk.StringVar(value=self.config_data.get('log_file_path'))
        self.enable_volume_var = tk.BooleanVar(value=self.config_data.get('enable_volume_adjustment'))
        self.volume_level_var = tk.DoubleVar(value=self.config_data.get('volume_level'))

        self.settings_map = {
            'interactive_selection': self.interactive_var,
            'ffmpeg_path': self.ffmpeg_var,
            'download_subtitles': self.sub_dl_var,
            'embed_subtitles': self.sub_embed_var,
            'makedirector': self.makedir_var,
            'enable_logging': self.enable_logging_var,
            'log_file_path': self.log_path_var,
            'enable_volume_adjustment': self.enable_volume_var,
            'volume_level': self.volume_level_var,
        }

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        self._create_directory_section(main_frame)
        self._create_mode_section(main_frame)
        self._create_other_settings_section(main_frame)
        self._create_log_config_section(main_frame)
        self._create_bottom_buttons(main_frame)

        self._update_log_controls()
        self._update_volume_controls()

    def _create_directory_section(self, parent):
        dir_section = ttk.LabelFrame(parent, text='ダウンロード先ディレクトリ', padding=5)
        dir_section.pack(fill='both', expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(dir_section)
        btn_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(btn_frame, text='ディレクトリを追加', command=self.add_directory).pack(side='left')
        ttk.Label(btn_frame, text='※ディレクトリを追加後、パスを設定してください').pack(side='left', padx=(10, 0))

        canvas = tk.Canvas(dir_section, height=200)
        scrollbar = ttk.Scrollbar(dir_section, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._build_directory_list()

    def _create_mode_section(self, parent):
        mode_frame = ttk.LabelFrame(parent, text="ディレクトリ選択モード", padding=5)
        mode_frame.pack(fill='x', pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="json準拠の設定", variable=self.interactive_var, value=False).pack(anchor='w')
        ttk.Radiobutton(mode_frame, text="実行時に対話的選択", variable=self.interactive_var, value=True).pack(anchor='w')

    def _create_other_settings_section(self, parent):
        other_frame = ttk.LabelFrame(parent, text="その他の設定", padding=5)
        other_frame.pack(fill='x', pady=(0, 10))

        ffmpeg_frame = ttk.Frame(other_frame)
        ffmpeg_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(ffmpeg_frame, text='ffmpegパス:').pack(anchor='w')
        ffmpeg_entry_frame = ttk.Frame(ffmpeg_frame)
        ffmpeg_entry_frame.pack(fill='x', pady=(2, 0))
        ttk.Entry(ffmpeg_entry_frame, textvariable=self.ffmpeg_var).pack(side='left', fill='x', expand=True)
        ttk.Button(ffmpeg_entry_frame, text='選択', command=self.choose_ffmpeg).pack(side='right', padx=(5, 0))

        for text, var in [('字幕をダウンロード', self.sub_dl_var), ('字幕を埋め込み', self.sub_embed_var), ('プレイリストの場合のディレクトリ作成する', self.makedir_var)]:
            ttk.Checkbutton(other_frame, text=text, variable=var).pack(anchor='w', pady=2)

        self.volume_check = ttk.Checkbutton(other_frame, text='音量を調整する', variable=self.enable_volume_var, command=self._update_volume_controls)
        self.volume_check.pack(anchor='w', pady=(10, 2))
        self.volume_frame = ttk.Frame(other_frame)
        self.volume_frame.pack(fill='x', padx=20, pady=(0, 5))
        self.volume_label_var = tk.StringVar(value=f"{self.volume_level_var.get():.2f}")
        self.volume_scale = ttk.Scale(self.volume_frame, from_=0.0, to=2.0, orient='horizontal', variable=self.volume_level_var, command=lambda s: self.volume_label_var.set(f"{float(s):.2f}"))
        self.volume_scale.pack(side='left', fill='x', expand=True)
        self.volume_label = ttk.Label(self.volume_frame, textvariable=self.volume_label_var, width=5)
        self.volume_label.pack(side='right')

    def _create_log_config_section(self, parent):
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

    def _create_bottom_buttons(self, parent):
        bottom_btn_frame = ttk.Frame(parent)
        bottom_btn_frame.pack(fill='x', pady=(10, 0))
        ttk.Button(bottom_btn_frame, text='保存して終了', command=self.on_save_and_exit).pack(side='left', padx=(0, 5))
        ttk.Button(bottom_btn_frame, text='設定ファイルを開く', command=self.open_config).pack(side='left', padx=5)

    def _update_volume_controls(self):
        state = 'normal' if self.enable_volume_var.get() else 'disabled'
        self.volume_scale.config(state=state)
        self.volume_label.config(foreground='black' if state == 'normal' else 'grey')

    def _update_log_controls(self):
        state = 'normal' if self.enable_logging_var.get() else 'disabled'
        for widget in [self.log_path_entry, self.log_path_btn, self.log_path_label]:
            widget.config(state=state) if not isinstance(widget, ttk.Label) else widget.config(foreground='black' if state == 'normal' else 'gray')

    def _build_directory_list(self):
        for widgets in self.dir_widgets:
            widgets['frame'].destroy()
        self.dir_widgets.clear()
        for i, dir_info in enumerate(self.config_data['directories']):
            self._create_directory_row(i, dir_info)
        self.scrollable_frame.update_idletasks()

    def _create_directory_row(self, index, dir_info):
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill='x', pady=2, padx=5)
        widgets = {'frame': row_frame}

        widgets['radio'] = ttk.Radiobutton(row_frame, text=f"候補{index + 1}", variable=self.dir_var, value=index)
        widgets['radio'].pack(side='left')

        widgets['path_var'] = tk.StringVar(value=dir_info['path'])
        widgets['path_entry'] = ttk.Entry(row_frame, textvariable=widgets['path_var'], width=40)
        widgets['path_entry'].pack(side='left', fill='x', expand=True, padx=(5, 0))

        widgets['format_var'] = tk.StringVar(value=dir_info['format'])
        widgets['format_combo'] = ttk.Combobox(row_frame, textvariable=widgets['format_var'], values=['mp3', 'mp4', 'webm', 'wav', 'flac'], width=8, state='readonly')
        widgets['format_combo'].pack(side='right', padx=(5, 0))

        widgets['select_btn'] = ttk.Button(row_frame, text='選択', command=lambda idx=index: self.change_dir(idx))
        widgets['select_btn'].pack(side='right', padx=(5, 0))

        widgets['delete_btn'] = ttk.Button(row_frame, text='削除', command=lambda idx=index: self.delete_directory(idx))
        widgets['delete_btn'].pack(side='right', padx=(5, 0))
        if len(self.config_data['directories']) <= 1:
            widgets['delete_btn'].config(state='disabled')
        
        self.dir_widgets.append(widgets)

    def add_directory(self):
        self.config_data['directories'].append({"path": "", "format": "mp3"})
        self._build_directory_list()
        messagebox.showinfo('追加完了', f'新しいディレクトリ候補{len(self.config_data["directories"])}を追加しました。\nパスを設定してください。')

    def delete_directory(self, index):
        if len(self.config_data['directories']) <= 1:
            return messagebox.showwarning('警告', '最低1つのディレクトリは必要です。')
        
        dir_path = self.dir_widgets[index]['path_var'].get() or f"候補{index + 1}"
        if messagebox.askyesno('確認', f'"{dir_path}"を削除しますか？'):
            self.config_data['directories'].pop(index)
            if self.dir_var.get() >= len(self.config_data['directories']):
                self.dir_var.set(len(self.config_data['directories']) - 1)
            self._build_directory_list()

    def change_dir(self, index):
        if new_path := filedialog.askdirectory(title=f'候補{index + 1}のディレクトリを選択'):
            self.dir_widgets[index]['path_var'].set(new_path)

    def choose_ffmpeg(self):
        if path := filedialog.askopenfilename(title='ffmpegの実行ファイルを選択', filetypes=[('Executable', '*.exe'), ('All files', '*.*')]):
            self.ffmpeg_var.set(path)

    def choose_log_file(self):
        if path := filedialog.asksaveasfilename(title='ログファイルの保存先を選択', defaultextension='.json', filetypes=[('JSON files', '*.json'), ('All files', '*.*')]):
            self.log_path_var.set(path)

    def _open_path(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path], check=True)
            else:
                subprocess.run(['xdg-open', path], check=True)
        except Exception as e:
            messagebox.showerror('エラー', f'パスを開けませんでした: {e}\nパス: {path}')

    def open_config(self):
        self._open_path(CONFIG_FILE)

    def on_save(self):
        directories = [d for w in self.dir_widgets if (d := {"path": w['path_var'].get().strip(), "format": w['format_var'].get()})['path']]
        if not directories:
            messagebox.showwarning('警告', '最低1つのディレクトリを設定してください。')
            return False
        
        if self.enable_logging_var.get() and not self.log_path_var.get().strip():
            if not messagebox.askyesno('確認', 'ログ機能が有効ですが、ログファイルパスが設定されていません。\nこのまま保存しますか？'):
                return False
        
        self.config_data['directories'] = directories
        self.config_data['default_directory_index'] = min(self.dir_var.get(), len(directories) - 1)
        for key, var in self.settings_map.items():
            value = var.get()
            if isinstance(var, tk.DoubleVar): value = round(value, 2)
            self.config_data[key] = value
        
        try:
            save_config(self.config_data)
            return True
        except Exception as e:
            messagebox.showerror('エラー', f'設定の保存に失敗しました: {e}')
            return False

    def on_save_and_exit(self):
        if self.on_save():
            self.destroy()

if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()