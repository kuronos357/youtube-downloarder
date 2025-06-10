import os
import json
import pyperclip
import logging
from pathlib import Path
from yt_dlp import YoutubeDL
from typing import Dict, List, Optional, Tuple

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self, config_path: str = "python/youtube-downloarder/設定json/config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_ffmpeg()
    
    def _load_config(self) -> Dict:
        """設定ファイルを読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = json.load(file)
                logger.info("設定ファイルを正常に読み込みました")
                return config
        except FileNotFoundError:
            logger.error(f"設定ファイルが見つかりません: {self.config_path}")
            return self._create_default_config()
        except json.JSONDecodeError:
            logger.error("設定ファイルのJSON形式が無効です")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """デフォルト設定を作成"""
        default_config = {
            "default_directory": "./downloads",
            "default_format": "mp4",
            "download_subtitles": False,
            "embed_subtitles": False,
            "ffmpeg_path": "ffmpeg"
        }
        logger.info("デフォルト設定を使用します")
        return default_config
    
    def _setup_ffmpeg(self):
        """FFmpegのパスを設定"""
        ffmpeg_path = self.config.get('ffmpeg_path', 'ffmpeg')
        if ffmpeg_path != 'ffmpeg' and os.path.exists(ffmpeg_path):
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            if ffmpeg_dir not in os.environ['PATH']:
                os.environ['PATH'] += os.pathsep + ffmpeg_dir
                logger.info(f"FFmpegパスを追加: {ffmpeg_dir}")
    
    def _get_base_options(self, output_dir: str) -> Dict:
        """基本的なダウンロードオプションを取得"""
        return {
            'outtmpl': str(Path(output_dir) / '%(title)s.%(ext)s'),
            'writeinfojson': True,  # メタデータ保存
            'writethumbnail': True,  # サムネイル保存
            'embedsubs': self.config.get('embed_subtitles', False),
            'writesubtitles': self.config.get('download_subtitles', False),
            'subtitleslangs': ['ja', 'en'] if self.config.get('download_subtitles', False) else [],
            # YouTube制限回避のための設定
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios'],
                    'skip': ['hls']
                }
            },
            # エラー処理の改善
            'ignoreerrors': False,
            'no_warnings': False,
        }
    
    def _get_format_options(self, format_choice: str) -> Tuple[str, List[Dict]]:
        """形式に応じたフォーマット文字列とポストプロセッサを取得"""
        postprocessors = []
        
        if format_choice.lower() == "mp4":
            # MP4: 複数のフォールバックを用意
            format_str = (
                'best[ext=mp4][height<=1080]/best[ext=mp4][height<=720]/'
                'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
                'best[height<=1080]/best[height<=720]/best'
            )
            logger.info("MP4形式でダウンロードします")
            
        elif format_choice.lower() == "webm":
            # WebM: より柔軟な指定
            format_str = (
                'best[ext=webm][height<=1080]/best[ext=webm][height<=720]/'
                'best[ext=webm]/bestvideo[ext=webm]+bestaudio[ext=webm]/'
                'best[height<=1080]/best[height<=720]/best'
            )
            logger.info("WebM形式でダウンロードします")
            
        elif format_choice.lower() == "mp3":
            # MP3: 音声のみ
            format_str = 'bestaudio/best'
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            logger.info("MP3形式でダウンロードします")
            
        else:
            # その他: 最も確実な形式
            format_str = 'best[height<=720]/best'
            logger.info("利用可能な最良の形式でダウンロードします")
        
        return format_str, postprocessors
    
    def _create_download_options(self, output_dir: str, format_choice: str) -> Dict:
        """完全なダウンロードオプションを作成"""
        options = self._get_base_options(output_dir)
        format_str, postprocessors = self._get_format_options(format_choice)
        
        options['format'] = format_str
        if postprocessors:
            options['postprocessors'] = postprocessors
        
        # 字幕埋め込みの追加設定
        if self.config.get('embed_subtitles', False) and format_choice.lower() != 'mp3':
            if 'postprocessors' not in options:
                options['postprocessors'] = []
            options['postprocessors'].append({
                'key': 'FFmpegEmbedSubtitle',
            })
        
        return options
    
    def _download_with_multiple_methods(self, url: str, output_dir: str, format_choice: str) -> bool:
        """複数の方法でダウンロードを試行"""
        methods = [
            ("標準方法", lambda: self._download_standard(url, output_dir, format_choice)),
            ("Android クライアント", lambda: self._download_android_client(url, output_dir)),
            ("最低品質フォールバック", lambda: self._download_minimal(url, output_dir)),
        ]
        
        for method_name, download_func in methods:
            try:
                logger.info(f"{method_name}でダウンロードを試行中...")
                download_func()
                logger.info(f"{method_name}でダウンロードが完了しました")
                return True
            except Exception as e:
                logger.warning(f"{method_name}が失敗: {str(e)}")
                continue
        
        logger.error("すべてのダウンロード方法が失敗しました")
        return False
    
    def _download_standard(self, url: str, output_dir: str, format_choice: str):
        """標準的な方法でダウンロード"""
        options = self._create_download_options(output_dir, format_choice)
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    
    def _download_android_client(self, url: str, output_dir: str):
        """Androidクライアントでダウンロード"""
        options = {
            'outtmpl': str(Path(output_dir) / '%(title)s.%(ext)s'),
            'format': 'best[height<=720]/best',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            }
        }
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    
    def _download_minimal(self, url: str, output_dir: str):
        """最小限の設定でダウンロード"""
        options = {
            'outtmpl': str(Path(output_dir) / '%(title)s.%(ext)s'),
            'format': 'worst/best',
            'no_warnings': True,
        }
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    
    def get_playlist_info(self, playlist_url: str) -> Tuple[List[str], str]:
        """プレイリストから動画URLリストを取得"""
        options = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            }
        }
        
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' in info and info['entries']:
                    video_urls = []
                    for entry in info['entries']:
                        if entry and 'url' in entry:
                            video_urls.append(entry['url'])
                        elif entry and 'id' in entry:
                            # URLが直接取得できない場合はIDから構築
                            video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                    
                    playlist_title = info.get('title', 'プレイリスト')
                    logger.info(f"プレイリスト '{playlist_title}' から {len(video_urls)} 個の動画を取得")
                    return video_urls, playlist_title
                else:
                    logger.warning("プレイリストに動画が見つかりませんでした")
                    return [], 'プレイリスト'
                    
        except Exception as e:
            logger.error(f"プレイリスト情報の取得に失敗: {str(e)}")
            return [], 'プレイリスト'
    
    def download_single_video(self, url: str, output_dir: str, format_choice: str) -> bool:
        """単一動画をダウンロード"""
        logger.info(f"動画のダウンロードを開始: {url}")
        return self._download_with_multiple_methods(url, output_dir, format_choice)
    
    def download_playlist(self, playlist_url: str, output_dir: str, format_choice: str) -> bool:
        """プレイリストをダウンロード"""
        video_urls, playlist_title = self.get_playlist_info(playlist_url)
        
        if not video_urls:
            logger.error("プレイリストから動画URLを取得できませんでした")
            return False
        
        # プレイリスト用ディレクトリを作成
        playlist_dir = Path(output_dir) / self._sanitize_filename(playlist_title)
        playlist_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"プレイリスト '{playlist_title}' の {len(video_urls)} 個の動画をダウンロード開始")
        
        success_count = 0
        for i, video_url in enumerate(video_urls, 1):
            logger.info(f"動画 {i}/{len(video_urls)} をダウンロード中...")
            if self.download_single_video(video_url, str(playlist_dir), format_choice):
                success_count += 1
            else:
                logger.warning(f"動画 {i} のダウンロードに失敗")
        
        logger.info(f"プレイリストダウンロード完了: {success_count}/{len(video_urls)} 成功")
        return success_count > 0
    
    def _sanitize_filename(self, filename: str) -> str:
        """ファイル名から無効な文字を除去"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def validate_config(self) -> bool:
        """設定の妥当性を検証"""
        output_dir = self.config.get('default_directory', '')
        if not output_dir:
            logger.error("保存先ディレクトリが設定されていません")
            return False
        
        # ディレクトリが存在しない場合は作成を試行
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"保存先ディレクトリ: {output_dir}")
            return True
        except Exception as e:
            logger.error(f"保存先ディレクトリの作成に失敗: {str(e)}")
            return False
    
    def run(self):
        """メイン実行処理"""
        logger.info("YouTube ダウンローダーを開始")
        
        # 設定の検証
        if not self.validate_config():
            return
        
        # クリップボードからURLを取得
        try:
            video_url = pyperclip.paste().strip()
        except Exception as e:
            logger.error(f"クリップボードの読み取りに失敗: {str(e)}")
            return
        
        if not video_url or "youtube.com" not in video_url and "youtu.be" not in video_url:
            logger.error("クリップボードに有効なYouTube URLが見つかりません")
            return
        
        logger.info(f"URL を検出: {video_url}")
        
        # 設定値を取得
        output_dir = self.config.get('default_directory')
        format_choice = self.config.get('default_format', 'mp4')
        
        # プレイリストか単一動画かを判定してダウンロード
        try:
            if any(keyword in video_url.lower() for keyword in ['playlist', 'list=']):
                success = self.download_playlist(video_url, output_dir, format_choice)
            else:
                success = self.download_single_video(video_url, output_dir, format_choice)
            
            if success:
                logger.info("ダウンロード処理が完了しました")
            else:
                logger.error("ダウンロード処理が失敗しました")
                
        except KeyboardInterrupt:
            logger.info("ユーザーによって中断されました")
        except Exception as e:
            logger.error(f"予期しないエラーが発生: {str(e)}")

def main():
    """エントリーポイント"""
    downloader = YouTubeDownloader()
    downloader.run()

if __name__ == "__main__":
    main()