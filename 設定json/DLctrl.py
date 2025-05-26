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
    "directory1": "/mnt/chromeos/PlayFiles/Music/BGM",
    "directory2": "/mnt/chromeos/PlayFiles/Movies",
    "directory3": "/mnt/chromeos/PlayFiles/Podcasts",
    "default_directory": "/mnt/chromeos/PlayFiles/Music/BGM",
    "default_format": "mp3",
    "ffmpeg_path": "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe",
    "download_subtitles": False,
    "embed_subtitles": False,
    "makedirector": True
}

# 設定ファイルを読み込む関数
def load_config():
    # CONFIG_FILEが存在する場合、JSON形式で読み込み設定を取得
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 存在しない場合はデフォルト設定を返す
    return DEFAULT_CONFIG.copy()

# 設定ファイルに設定情報を書き込む関数
def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        # インデント付きでJSONデータを保存
        json.dump(config, f, indent=4, ensure_ascii=False)

# ConfigGUIクラス: 設定画面のためのメインウィンドウクラス
class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('設定マネージャー')  # ウィンドウタイトル
        self.resizable(True, True)  # ウィンドウサイズ固定
        # 設定を読み込み、保存先用のディクショナリに格納する
        self.config_data = load_config()
        self.dir_radios = []  # ダウンロード先ディレクトリ用のラジオボタンのリスト
        self._create_vars()  # 各種変数を初期化
        self._build_ui()  # GUIレイアウトの構築

    # GUIで使用する各種変数（tkinter変数）の作成
    def _create_vars(self):
        self.dir_var = tk.StringVar(value=self.config_data.get('default_directory', ''))  # 選択中のディレクトリ
        self.format_var = tk.StringVar(value=self.config_data.get('default_format', 'mp3'))  # 選択中のファイル形式
        self.ffmpeg_var = tk.StringVar(value=self.config_data.get('ffmpeg_path', ''))  # ffmpegのパス
        self.sub_dl_var = tk.BooleanVar(value=self.config_data.get('download_subtitles', False))  # 字幕ダウンロード設定
        self.sub_embed_var = tk.BooleanVar(value=self.config_data.get('embed_subtitles', False))  # 字幕埋め込み設定
        self.makedir_var = tk.BooleanVar(value=self.config_data.get('mkdir_list', True))  # ディレクトリ作成設定

    # GUIのウィジェット構築
    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.grid()

        # ダウンロード先ディレクトリの設定セクション
        ttk.Label(frame, text='ダウンロード先ディレクトリ:').grid(row=0, column=0, columnspan=2, sticky='w')
        # 3つの候補ディレクトリに対してラジオボタンと変更ボタンを配置
        for i in range(1, 4):
            key = f'directory{i}'  # 設定キーの生成
            path = self.config_data.get(key, '')
            # ラジオボタンでディレクトリを選択できるようにする
            rb = ttk.Radiobutton(
                frame,
                text=f'候補{i}: {path}',
                variable=self.dir_var,
                value=path
            )
            rb.grid(row=i, column=0, sticky='w', pady=2)
            # ラジオボタンと対応するキーをリストに追加（後で更新時に利用）
            self.dir_radios.append((rb, key))
            # 「変更」ボタンでディレクトリの変更ダイアログを表示
            btn = ttk.Button(
                frame,
                text='変更',
                command=lambda k=key, idx=i: self.change_dir(k, idx)
            )
            btn.grid(row=i, column=1, padx=5)

        # 出力フォーマットの選択セクション
        ttk.Label(frame, text='出力フォーマット:').grid(row=4, column=0, sticky='w', pady=(10, 0))
        formats = ['mp3', 'webm', 'mp4']  # 利用可能なフォーマット
        # 各フォーマットに対してラジオボタンを配置
        for j, fmt in enumerate(formats, start=5):
            ttk.Radiobutton(
                frame,
                text=fmt,
                variable=self.format_var,
                value=fmt
            ).grid(row=j, column=0, sticky='w')

        # ffmpegパス設定セクション
        ttk.Label(frame, text='ffmpegパス:').grid(row=8, column=0, sticky='w', pady=(10, 0))
        # 入力エントリでパスを表示・編集
        entry = ttk.Entry(frame, textvariable=self.ffmpeg_var, width=40)
        entry.grid(row=9, column=0, columnspan=2)
        # 「選択」ボタンでファイル選択ダイアログを開く
        ttk.Button(frame, text='選択', command=self.choose_ffmpeg).grid(row=9, column=2, padx=5)

        # 字幕関連の設定セクション
        ttk.Checkbutton(frame, text='字幕をダウンロード', variable=self.sub_dl_var).grid(row=10, column=0, sticky='w', pady=(10, 0))
        ttk.Checkbutton(frame, text='字幕を埋め込み', variable=self.sub_embed_var).grid(row=11, column=0, sticky='w')

        # プレイリスト対象のディレクトリ作成設定
        ttk.Checkbutton(frame, text='プレイリストの場合のディレクトリ作成する', variable=self.makedir_var).grid(row=12, column=0, sticky='w')

        # 操作用ボタンの配置エリア
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=13, column=0, columnspan=3, pady=15)
        # 「保存」ボタンで設定内容をファイルに書き込み
        ttk.Button(btn_frame, text='保存', command=self.on_save).grid(row=0, column=0, padx=5)
        # 「設定ファイルを開く」ボタンで設定ファイルをエディタで開く
        ttk.Button(btn_frame, text='設定ファイルを開く', command=self.open_config).grid(row=0, column=1, padx=5)
        # 「終了」ボタンでアプリケーションを終了する
        ttk.Button(btn_frame, text='終了', command=self.destroy).grid(row=0, column=2, padx=5)

    # ディレクトリ変更用の関数
    def change_dir(self, key, idx):
        # ユーザーにディレクトリを選択させるダイアログを表示
        new_path = filedialog.askdirectory()
        if not new_path:
            return  # キャンセルされた場合は何もせず終了
        # 選択されたディレクトリを設定データに更新
        self.config_data[key] = new_path
        # 関連するラジオボタンの表示テキストと値を更新する
        for rb, rb_key in self.dir_radios:
            if rb_key == key:
                rb.config(text=f'候補{idx}: {new_path}', value=new_path)
        # 選択中のディレクトリ変数も更新
        self.dir_var.set(new_path)

    # ffmpegパス選択用の関数
    def choose_ffmpeg(self):
        # ファイル選択ダイアログを開き、実行可能ファイルの選択を促す
        path = filedialog.askopenfilename(filetypes=[('Executable', '*.exe'), ('All files', '*.*')])
        if path:
            # 選択されたパスを設定変数にセット
            self.ffmpeg_var.set(path)

    # 設定ファイルを外部プログラムで開くための関数
    def open_config(self):
        try:
            # OSに応じた方法で設定ファイルを開く
            if os.name == 'nt':  # Windowsの場合
                os.startfile(CONFIG_FILE)
            elif sys.platform == 'darwin':  # macOSの場合
                subprocess.Popen(['open', str(CONFIG_FILE)])
            else:  # Linuxなどの場合
                subprocess.Popen(['xdg-open', str(CONFIG_FILE)])
        except Exception as e:
            # エラー発生時にはエラーダイアログでユーザーに通知
            messagebox.showerror('エラー', f'設定ファイルを開けませんでした: {e}')

    # 設定内容を保存するための関数
    def on_save(self):
        # GUI上の各設定値をconfig_dataに反映させる
        self.config_data['default_directory'] = self.dir_var.get()
        self.config_data['default_format'] = self.format_var.get()
        self.config_data['ffmpeg_path'] = self.ffmpeg_var.get()
        self.config_data['download_subtitles'] = self.sub_dl_var.get()
        self.config_data['embed_subtitles'] = self.sub_embed_var.get()
        self.config_data['mkdir_list']=self.makedir_var.get()
        # 設定ファイルに書き込む
        save_config(self.config_data)
        # ユーザーへ保存完了の通知を表示
        messagebox.showinfo('保存', '設定を保存しました。')

# メイン処理: スクリプトとして直接実行された場合、GUIを起動
if __name__ == '__main__':
    app = ConfigGUI()
    app.mainloop()