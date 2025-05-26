from yt_dlp import YoutubeDL
import os

path = 'C:/Users/hoge/ffmpeg-win64/bin' 
os.environ['PATH'] +=  '' if path in os.environ['PATH'] else ';' + path

#オプションを指定（最高画質の動画と最高音質の音声を取り出し結合するためのオプション）
option = {
        'outtmpl' : 'D:\ダウンロード\新しいフォルダー/%(title)s.%(ext)s',
        'format' : 'bestvideo+bestaudio/best'
    }

#インスタンスの生成
ydl = YoutubeDL(option)

#ダウンロードの実行
result = ydl.download(['https://youtu.be/JSB7776dCDc?si=zNPjBKgw5EttZirl'])