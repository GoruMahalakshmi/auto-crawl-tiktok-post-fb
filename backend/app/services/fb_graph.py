import requests
import os
import time

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def _build_graph_error_message(data, status_code: int) -> str:
    error = data.get("error", {}) if isinstance(data, dict) else {}
    if error.get("message"):
        return error["message"]
    return f"Facebook Graph API trả về lỗi {status_code}."


def _parse_graph_response(response):
    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.ok and "error" not in data:
        return {
            "ok": True,
            "status_code": response.status_code,
            "data": data,
        }

    return {
        "ok": False,
        "status_code": response.status_code,
        "data": data,
        "message": _build_graph_error_message(data, response.status_code),
    }


def _graph_get(path: str, *, params: dict | None = None, timeout: int = 30):
    response = requests.get(f"{GRAPH_API_BASE}/{path.lstrip('/')}", params=params, timeout=timeout)
    return _parse_graph_response(response)


def _graph_post(path: str, *, data: dict | None = None, json_payload: dict | None = None, params: dict | None = None, timeout: int = 30):
    response = requests.post(
        f"{GRAPH_API_BASE}/{path.lstrip('/')}",
        data=data,
        json=json_payload,
        params=params,
        timeout=timeout,
    )
    return _parse_graph_response(response)

def upload_video_to_facebook(file_path: str, caption: str, page_id: str, access_token: str):
    """ 
    Tải video trực tiếp lên Facebook Reels bằng Graph API 3 bước (khởi tạo -> tải lên -> công bố).
    Quy trình này ổn định hơn nhiều cho Reels so với việc đẩy file 1 lần.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    # Nếu người dùng vẫn nhập URL webhook cũ, báo lỗi yêu cầu đổi sang mã truy cập thật
    if access_token.startswith("http://") or access_token.startswith("https://"):
        return {'error': 'Vui lòng thay URL webhook bằng mã truy cập trang Facebook thật trong cấu hình.'}

    try:
        # Giai đoạn 1: Khởi tạo
        print(f"FB GHI CHÚ: Khởi tạo tải Reels cho trang {page_id}...")
        init_url = f"{GRAPH_API_BASE}/{page_id}/video_reels"
        params = {
            'upload_phase': 'start',
            'access_token': access_token
        }
        res_init = requests.post(init_url, params=params, timeout=30)
        res_init_data = res_init.json()
        
        if 'video_id' not in res_init_data:
            print(f"FB LỖI (khởi tạo - toàn bộ JSON): {res_init_data}")
            return {'error': f"Lỗi khởi tạo Reels: {res_init_data.get('error', {}).get('message', 'Lỗi không xác định')}"}
        
        video_id = res_init_data['video_id']
        print(f"FB GHI CHÚ: Đã lấy mã video: {video_id}")

        # Giai đoạn 2: Tải lên - Dùng hạ tầng RUpload chuyên dụng
        print("FB GHI CHÚ: Đang tải dữ liệu video lên hạ tầng RUpload...")
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
            # Tải toàn bộ tệp lên rupload
            res_upload = requests.post(
                upload_url, 
                data=f, 
                headers=headers,
                timeout=300 # Cho phép 5 phút để tải lên
            )
        
        res_upload_data = res_upload.json()
        # Chú ý: RUpload có thể trả về thành công theo kiểu khác, nên kiểm tra 'id' hoặc 'success'
        if 'id' not in res_upload_data and not res_upload_data.get('success'):
            print(f"FB LỖI (RUpload - toàn bộ JSON): {res_upload_data}")
            return {'error': f"Lỗi tải video (RUpload): {res_upload_data.get('error', {}).get('message', 'Tải video thất bại')}"}

        # Giai đoạn 3: Hoàn tất và công bố
        print("FB GHI CHÚ: Đợi 20 giây để Facebook xử lý video trước khi công bố...")
        time.sleep(20) # Thời gian chờ rất quan trọng cho video lớn

        print("FB GHI CHÚ: Đang hoàn tất và công bố Reel...")
        publish_url = f"{GRAPH_API_BASE}/{page_id}/video_reels"
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
            print(f"FB THÀNH CÔNG: Đã đăng Reel thành công. Mã video: {video_id}")
            return {'id': video_id}
        else:
            print(f"FB LỖI (công bố - toàn bộ JSON): {res_publish_data}")
            error_msg = res_publish_data.get('error', {}).get('message', 'Công bố thất bại')
            return {'error': f"Lỗi công bố: {error_msg}"}

    except Exception as e:
        print(f"FB LỖI NGHIÊM TRỌNG: {str(e)}")
        return {'error': f"Lỗi hệ thống khi đăng FB: {str(e)}"}


def inspect_page_access(page_id: str, access_token: str):
    try:
        token_subject = _graph_get(
            "me",
            params={
                "fields": "id,name",
                "access_token": access_token,
            },
            timeout=30,
        )
        if not token_subject["ok"]:
            return {
                "ok": False,
                "message": token_subject["message"],
                "token_kind": "invalid_token",
            }

        page_result = _graph_get(
            page_id,
            params={
                "fields": "id,name,link,fan_count",
                "access_token": access_token,
            },
            timeout=30,
        )
        if not page_result["ok"]:
            return {
                "ok": False,
                "message": page_result["message"],
                "token_kind": "invalid_token",
                "token_subject_id": token_subject["data"].get("id"),
                "token_subject_name": token_subject["data"].get("name"),
            }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Không thể kết nối tới Facebook Graph API: {exc}",
            "token_kind": "network_error",
        }

    token_subject_id = token_subject["data"].get("id")
    token_subject_name = token_subject["data"].get("name")
    page_data = page_result["data"]
    is_page_token = token_subject_id == page_id

    if not is_page_token:
        return {
            "ok": False,
            "message": "Mã truy cập hiện tại là User Access Token. Hãy dùng đúng Page Access Token của fanpage.",
            "token_kind": "user_access_token",
            "token_subject_id": token_subject_id,
            "token_subject_name": token_subject_name,
            "page_id": page_data.get("id", page_id),
            "page_name": page_data.get("name"),
        }

    return {
        "ok": True,
        "message": f"Mã truy cập hợp lệ cho trang Facebook {page_data.get('name', page_id)}.",
        "token_kind": "page_access_token",
        "token_subject_id": token_subject_id,
        "token_subject_name": token_subject_name,
        "page_id": page_data.get("id", page_id),
        "page_name": page_data.get("name"),
        "page_link": page_data.get("link"),
        "fan_count": page_data.get("fan_count"),
    }


def inspect_page_messenger_subscription(page_id: str, access_token: str, *, required_fields: tuple[str, ...] = ("messages",)):
    try:
        result = _graph_get(
            f"{page_id}/subscribed_apps",
            params={
                "fields": "id,name,subscribed_fields",
                "access_token": access_token,
            },
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "connected": False,
            "message": f"Không thể kiểm tra kết nối Messenger: {exc}",
            "required_fields": list(required_fields),
            "apps": [],
        }

    if not result["ok"]:
        return {
            "ok": False,
            "connected": False,
            "message": result["message"],
            "required_fields": list(required_fields),
            "apps": [],
        }

    apps = []
    for app in result["data"].get("data", []):
        fields = app.get("subscribed_fields") or []
        apps.append(
            {
                "id": app.get("id"),
                "name": app.get("name"),
                "subscribed_fields": fields,
            }
        )

    connected_app = next(
        (
            app
            for app in apps
            if all(field in (app.get("subscribed_fields") or []) for field in required_fields)
        ),
        None,
    )

    if connected_app:
        return {
            "ok": True,
            "connected": True,
            "message": f"Inbox đã kết nối với app {connected_app.get('name') or connected_app.get('id')}.",
            "required_fields": list(required_fields),
            "connected_app": connected_app,
            "apps": apps,
        }

    return {
        "ok": True,
        "connected": False,
        "message": "Fanpage chưa đăng ký nhận webhook tin nhắn cho app này.",
        "required_fields": list(required_fields),
        "connected_app": None,
        "apps": apps,
    }


def subscribe_page_to_app(page_id: str, access_token: str, *, subscribed_fields: tuple[str, ...] = ("messages",)):
    try:
        result = _graph_post(
            f"{page_id}/subscribed_apps",
            data={
                "subscribed_fields": ",".join(dict.fromkeys(subscribed_fields)),
                "access_token": access_token,
            },
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Không thể đăng ký fanpage với app: {exc}",
        }

    if not result["ok"]:
        return {
            "ok": False,
            "message": result["message"],
            "data": result.get("data"),
        }

    return {
        "ok": bool(result["data"].get("success")),
        "message": "Đã đăng ký fanpage nhận webhook tin nhắn." if result["data"].get("success") else "Facebook không xác nhận đăng ký fanpage.",
        "data": result["data"],
    }

def reply_to_comment(comment_id: str, message: str, access_token: str):
    """Trả lời bình luận thông qua Graph API."""
    url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
    data = {
        'message': message,
        'access_token': access_token
    }
    try:
        res = requests.post(url, data=data, timeout=30)
        res_data = res.json()
        if 'error' in res_data:
            print(f"FB LỖI GRAPH: {res_data['error'].get('message')}")
        return res_data
    except Exception as e:
        print(f"Lỗi API trả lời Facebook: {e}")
        return None


def send_page_message(recipient_id: str, message: str, access_token: str):
    """Gửi phản hồi inbox từ fanpage qua Messenger Platform."""
    url = f"{GRAPH_API_BASE}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": message},
    }
    params = {"access_token": access_token}
    try:
        res = requests.post(url, params=params, json=payload, timeout=30)
        res_data = res.json()
        if "error" in res_data:
            print(f"FB LỖI MESSENGER: {res_data['error'].get('message')}")
        return res_data
    except Exception as e:
        print(f"Lỗi API gửi inbox Facebook: {e}")
        return None
