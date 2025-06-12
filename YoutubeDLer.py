import os
import json
import pyperclip
import logging
from pathlib import Path
from yt_dlp import YoutubeDL
from typing import Dict, List, Optional, Tuple, Any

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
            raise
        except json.JSONDecodeError:
            logger.error("設定ファイルのJSON形式が無効です")
            raise
    
    def _setup_ffmpeg(self):
        """FFmpegのパスを設定"""
        ffmpeg_path = self.config.get('ffmpeg_path', 'ffmpeg')
        if ffmpeg_path != 'ffmpeg' and os.path.exists(ffmpeg_path):
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            if ffmpeg_dir not in os.environ['PATH']:
                os.environ['PATH'] += os.pathsep + ffmpeg_dir
                logger.info(f"FFmpegパスを追加: {ffmpeg_dir}")
    
    def _get_base_options(self, output_dir: str) -> Dict:
        """基本的なダウンロードオプションを取得（設定ファイルベース）"""
        config = self.config
        
        options = {
            'outtmpl': str(Path(output_dir) / '%(title)s.%(ext)s'),
            'writeinfojson': config.get('write_info_json', False),
            'writethumbnail': config.get('write_thumbnail', False),
            'embedsubs': config.get('embed_subtitles', False),
            'writesubtitles': config.get('download_subtitles', False),
            'ignoreerrors': config.get('ignore_errors', False),
            'no_warnings': config.get('no_warnings', False),
        }
        
        # 字幕言語設定
        if config.get('download_subtitles', False):
            options['subtitleslangs'] = config.get('subtitle_languages', ['ja', 'en'])
        
        # YouTube制限回避設定
        youtube_args = {}
        if config.get('player_clients'):
            youtube_args['player_client'] = config.get('player_clients')
        if config.get('skip_formats'):
            youtube_args['skip'] = config.get('skip_formats')
        
        if youtube_args:
            options['extractor_args'] = {'youtube': youtube_args}
        
        # 高度な設定
        advanced = config.get('advanced_options', {})
        if advanced.get('socket_timeout'):
            options['socket_timeout'] = advanced['socket_timeout']
        if advanced.get('retries'):
            options['retries'] = advanced['retries']
        if advanced.get('fragment_retries'):
            options['fragment_retries'] = advanced['fragment_retries']
        if advanced.get('sleep_interval'):
            options['sleep_interval'] = advanced['sleep_interval']
        if advanced.get('max_sleep_interval'):
            options['max_sleep_interval'] = advanced['max_sleep_interval']
        
        return options
    
    def _substitute_format_variables(self, format_str: str) -> str:
        """フォーマット文字列内の変数を置換"""
        config = self.config
        variables = {
            'max_height': config.get('max_height', 1080),
            'fallback_height': config.get('fallback_height', 720),
            'audio_quality': config.get('audio_quality', '192')
        }
        
        for var, value in variables.items():
            format_str = format_str.replace(f'{{{var}}}', str(value))
        
        return format_str
    
    def _get_format_options(self, format_choice: str) -> Tuple[str, List[Dict]]:
        """形式に応じたフォーマット文字列とポストプロセッサを取得（設定ファイルベース）"""
        format_options = self.config.get('format_options', {})
        format_config = format_options.get(format_choice.lower())
        
        if not format_config:
            logger.warning(f"フォーマット '{format_choice}' が見つかりません。デフォルトを使用します。")
            format_str = 'best'
            postprocessors = []
        else:
            # フォーマット文字列を取得・変数置換
            primary_format = format_config.get('primary_format', 'best')
            fallback_format = format_config.get('fallback_format', 'best')
            
            format_str = f"{self._substitute_format_variables(primary_format)}/{self._substitute_format_variables(fallback_format)}"
            
            # ポストプロセッサを取得
            postprocessors = []
            if 'postprocessor' in format_config:
                pp_config = format_config['postprocessor'].copy()
                # ポストプロセッサの設定内でも変数置換
                if 'preferredquality' in pp_config:
                    pp_config['preferredquality'] = self._substitute_format_variables(pp_config['preferredquality'])
                postprocessors.append(pp_config)
            
            # MP3形式の場合は自動的にポストプロセッサを追加
            if format_choice.lower() == 'mp3' and not postprocessors:
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': self.config.get('audio_quality', '192')
                })
        
        description = format_config.get('description', f'{format_choice}形式') if format_config else f'{format_choice}形式'
        logger.info(f"{description}でダウンロードします")
        
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
        """複数の方法でダウンロードを試行（設定に基づく）"""
        methods = [("標準方法", lambda: self._download_standard(url, output_dir, format_choice))]
        
        # 設定に基づいてフォールバック方法を追加
        if self.config.get('enable_android_fallback', True):
            methods.append(("Android クライアント", lambda: self._download_android_client(url, output_dir)))
        
        methods.append(("最低品質フォールバック", lambda: self._download_minimal(url, output_dir)))
        
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
        """Androidクライアントでダウンロード（設定ベース）"""
        options = self._get_base_options(output_dir)
        # フォールバック用の簡単な設定に上書き
        fallback_height = self.config.get('fallback_height', 720)
        options.update({
            'format': f'best[height<={fallback_height}]/best',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            }
        })
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
        }
        
        # YouTube設定を追加
        if self.config.get('player_clients'):
            options['extractor_args'] = {
                'youtube': {
                    'player_client': self.config['player_clients'][:1]  # 最初のクライアントのみ使用
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
        """プレイリストをダウンロード（設定ベース）"""
        video_urls, playlist_title = self.get_playlist_info(playlist_url)
        
        if not video_urls:
            logger.error("プレイリストから動画URLを取得できませんでした")
            return False
        
        # プレイリスト用ディレクトリの作成設定
        if self.config.get('mkdir_list', True):
            if self.config.get('makedirector', True):
                playlist_title = self._sanitize_filename(playlist_title)
            playlist_dir = Path(output_dir) / playlist_title
            playlist_dir.mkdir(parents=True, exist_ok=True)
            final_output_dir = str(playlist_dir)
        else:
            final_output_dir = output_dir
        
        logger.info(f"プレイリスト '{playlist_title}' の {len(video_urls)} 個の動画をダウンロード開始")
        
        success_count = 0
        
        for i, video_url in enumerate(video_urls, 1):
            logger.info(f"動画 {i}/{len(video_urls)} をダウンロード中...")
            try:
                if self.download_single_video(video_url, final_output_dir, format_choice):
                    success_count += 1
                else:
                    logger.warning(f"動画 {i} のダウンロードに失敗")
            except KeyboardInterrupt:
                logger.info("ユーザーによって中断されました")
                break
            except Exception as e:
                logger.error(f"動画 {i} で予期しないエラー: {str(e)}")
        
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
        
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"保存先ディレクトリ: {output_dir}")
        except Exception as e:
            logger.error(f"保存先ディレクトリの作成に失敗: {str(e)}")
            return False
        
        # フォーマット設定の確認
        default_format = self.config.get('default_format', 'mp4')
        format_options = self.config.get('format_options', {})
        if default_format not in format_options:
            logger.warning(f"デフォルトフォーマット '{default_format}' が format_options に存在しません")
        
        return True
    
    def print_available_formats(self):
        """利用可能なフォーマットを表示"""
        format_options = self.config.get('format_options', {})
        logger.info("利用可能なフォーマット:")
        for format_name, format_config in format_options.items():
            description = format_config.get('description', format_name)
            logger.info(f"  {format_name}: {description}")
    
    def run(self):
        """メイン実行処理"""
        # ログレベルを設定から適用
        log_level = self.config.get('log_level', 'INFO')
        logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        logger.info("YouTube ダウンローダーを開始")
        
        # 設定の検証
        if not self.validate_config():
            return
        
        # 利用可能フォーマットの表示
        self.print_available_formats()
        
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