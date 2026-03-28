import yt_dlp
import os
import uuid
from pathlib import Path

DOWNLOAD_DIR = "/app/downloads"

def extract_metadata(url: str):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'extract_flat': False, # get full info
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # If url is a user profile, this will return a playlist of videos
        info = ydl.extract_info(url, download=False)
        return info

def download_video(url: str, filename_prefix: str = "video"):
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    video_id = str(uuid.uuid4())
    filename = f"{filename_prefix}_{video_id}.mp4"
    out_path = os.path.join(DOWNLOAD_DIR, filename)

    ydl_opts = {
        'format': 'best[vcodec^=h264]/best[vcodec^=avc]/best', # Ép bằng chính xác tên h264 vì TikTok không dùng chữ avc
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out_path, video_id
    except Exception as e:
        print(f"Lỗi tải video {url}: {e}")
        return None, None
