import requests
import os
import time

def upload_video_to_facebook(file_path: str, caption: str, page_id: str, access_token: str):
    """ 
    Upload video trực tiếp lên Facebook Reels dùng Graph API 3-bước (Initialize -> Upload -> Publish).
    Quy trình này ổn định hơn nhiều cho Reels so với việc đẩy file 1 lần.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    # Nếu người dùng vẫn nhập URL (Webhook cũ), báo lỗi yêu cầu đổi Token thật
    if access_token.startswith("http://") or access_token.startswith("https://"):
        return {'error': 'Vui lòng thay Webhook URL bằng Page Access Token thật trong cấu hình Fanpage.'}

    base_url = "https://graph.facebook.com/v19.0"
    
    try:
        # Giai đoạn 1: Khởi tạo (Initialize)
        print(f"FB DEBUG: Khởi tạo upload Reels cho Page {page_id}...")
        init_url = f"{base_url}/{page_id}/video_reels"
        params = {
            'upload_phase': 'start',
            'access_token': access_token
        }
        res_init = requests.post(init_url, params=params, timeout=30)
        res_init_data = res_init.json()
        
        if 'video_id' not in res_init_data:
            print(f"FB ERROR (Init Full JSON): {res_init_data}")
            return {'error': f"Lỗi khởi tạo Reels: {res_init_data.get('error', {}).get('message', 'Unknown error')}"}
        
        video_id = res_init_data['video_id']
        print(f"FB DEBUG: Đã lấy video_id: {video_id}")

        # Giai đoạn 2: Tải lên (Upload) - Dùng hạ tầng RUpload chuyên dụng
        print(f"FB DEBUG: Đang tải dữ liệu video (~50MB) lên hạ tầng RUpload...")
        upload_url = f"https://rupload.facebook.com/video-upload/v19.0/{video_id}"
        
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            headers = {
                'Authorization': f'OAuth {access_token}',
                'offset': '0',
                'file_size': str(file_size),
                'X-Entity-Type': 'video/mp4',
                'X-Entity-Name': 'video.mp4'
            }
            # Upload toàn bộ file lên rupload
            res_upload = requests.post(
                upload_url, 
                data=f, 
                headers=headers,
                timeout=300 # Cho phép 5 phút để upload
            )
        
        res_upload_data = res_upload.json()
        # Chú ý: RUpload có thể trả về Success theo kiểu khác, ta check 'id' hoặc 'handle'
        if 'id' not in res_upload_data and not res_upload_data.get('success'):
            print(f"FB ERROR (Upload RUpload Full JSON): {res_upload_data}")
            return {'error': f"Lỗi tải video (RUpload): {res_upload_data.get('error', {}).get('message', 'Upload failed')}"}

        # Giai đoạn 3: Hoàn tất & Publish
        print(f"FB DEBUG: Đợi 20 giây để Facebook xử lý video 50MB+ trước khi Publish...")
        time.sleep(20) # Thời gian chờ cực kỳ quan trọng cho video lớn

        print(f"FB DEBUG: Đang hoàn tất và Publish Reel...")
        publish_url = f"{base_url}/{page_id}/video_reels"
        publish_params = {
            'upload_phase': 'finish',
            'video_id': video_id,
            'video_state': 'PUBLISHED',
            'description': caption,
            'access_token': access_token
        }
        res_publish = requests.post(publish_url, params=publish_params, timeout=30)
        res_publish_data = res_publish.json()

        if 'success' in res_publish_data and res_publish_data['success']:
            print(f"FB SUCCESS: Đã đăng Reel thành công. Video ID: {video_id}")
            return {'id': video_id}
        else:
            print(f"FB ERROR (Publish Full JSON): {res_publish_data}")
            error_msg = res_publish_data.get('error', {}).get('message', 'Publish failed')
            return {'error': f"Lỗi Publish: {error_msg}"}

    except Exception as e:
        print(f"FB CRITICAL ERROR: {str(e)}")
        return {'error': f"Lỗi hệ thống khi đăng FB: {str(e)}"}

def reply_to_comment(comment_id: str, message: str, access_token: str):
    """ Trả lời comment thông qua Graph API """
    url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
    data = {
        'message': message,
        'access_token': access_token
    }
    try:
        res = requests.post(url, data=data, timeout=30)
        res_data = res.json()
        if 'error' in res_data:
            print(f"FB GRAPH ERROR: {res_data['error'].get('message')}")
        return res_data
    except Exception as e:
        print(f"Lỗi API Reply FB: {e}")
        return None
