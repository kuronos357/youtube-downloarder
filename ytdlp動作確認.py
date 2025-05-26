import yt_dlp

url = "https://youtu.be/Nu3T5gUVVN4?si=weIn2Q65RxQhHERq"

# フォーマットを一覧表示
ydl_opts = {
    'listformats': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
