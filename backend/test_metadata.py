import yt_dlp
import json
import sys

def test_tiktok_metadata(url):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            # Chỉ lấy các trường liên quan đến caption/title
            interesting_fields = {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description'),
                'alt_title': info.get('alt_title'),
                'fulltitle': info.get('fulltitle'),
                'uploader': info.get('uploader'),
                'webpage_url': info.get('webpage_url')
            }
            print(json.dumps(interesting_fields, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.tiktok.com/@vneconomy.vn/video/7349940173516033281"
    test_tiktok_metadata(test_url)
