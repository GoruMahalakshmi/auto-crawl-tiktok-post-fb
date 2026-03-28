import requests
import time
from app.core.config import settings

def generate_caption(original_caption: str) -> str:
    if not settings.GEMINI_API_KEY:
        return f"{original_caption}\n\n#xuhuong #tiktok"
    
    # Sử dụng gemini-2.5-flash để có quota tốt hơn và độ ổn định cao
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    
    prompt = f"""Bạn là Trùm Copywriter chuyên viral content Facebook. Mệnh lệnh bắt buộc:
1. Viết lại caption sao cho kịch tính, thú vị, xài emoji hợp lý, độ dài 50-100 từ.
2. QUAN TRỌNG: Ngay lập tức loại bỏ toàn bộ hashtag cũ trong caption gốc.
3. Dựa vào nội dung, tự bổ sung 5-6 hashtag đỉnh cao, viral nhất, sinh ra gốc cho nền tảng Facebook (VD: #giaitri #tintuchot #haihuoc).
Kết quả chỉ trả về đoạn caption thuần túy, KHÔNG giải thích, KHÔNG có tiêu đề.

Caption gốc: {original_caption}"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    max_retries = 3
    retry_delay = 2 # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Kiểm tra cấu trúc response hợp lệ
                if 'candidates' in data and data['candidates'] and 'content' in data['candidates'][0]:
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    print(f"AI Warning: Cấu trúc response lạ: {data}")
            
            elif response.status_code == 429:
                print(f"AI Rate Limit (429) - Thử lại lần {attempt + 1}/{max_retries}...")
            else:
                print(f"AI API Error {response.status_code}: {response.text}")
                
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1)) # Exponential backoff
        except Exception as e:
            print(f"AI Exception (Lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

    # Nếu tất cả các lần thử đều thất bại, trả về bản gốc và thêm hashtag chung chung của FB
    return f"{original_caption}\n\n#giaitri #trending"

def generate_reply(user_message: str) -> str:
    if not settings.GEMINI_API_KEY:
        return "Cảm ơn bạn đã quan tâm nhé! 💖"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    prompt = f"Bạn là CSKH cho Fanpage giải trí TikTok. Trả lời comment khách hàng cực kỳ thân thiện, ngầu, và sinh động với emoji. Câu trả lời thật ngắn gọn.\n\nKhách hàng nhắc: {user_message}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"AI Reply Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"AI Reply Exception: {e}")
        
    return "Cảm ơn bạn yêu! 💖"
