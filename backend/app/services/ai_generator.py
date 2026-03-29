import requests
import time

from app.services.runtime_settings import resolve_runtime_value

GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_COMMENT_REPLY_PROMPT = (
    "Bạn là chăm sóc khách hàng cho fanpage Facebook. "
    "Hãy trả lời bình luận thật thân thiện, ngắn gọn, tự nhiên và phù hợp ngữ cảnh. "
    "Chỉ trả về nội dung câu trả lời, không giải thích thêm."
)
DEFAULT_MESSAGE_REPLY_PROMPT = (
    "Bạn là trợ lý tư vấn cho fanpage Facebook. "
    "Hãy trả lời tin nhắn inbox theo phong cách lịch sự, rõ ràng, hữu ích và chủ động gợi mở bước tiếp theo khi phù hợp. "
    "Chỉ trả về nội dung tin nhắn gửi cho khách."
)


def _generate_with_gemini(prompt: str, fallback: str, *, timeout: int = 20, max_retries: int = 3) -> str:
    gemini_api_key = resolve_runtime_value("GEMINI_API_KEY")
    if not gemini_api_key:
        return fallback

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={gemini_api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("candidates") and data["candidates"][0].get("content"):
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

    return fallback


def generate_caption(original_caption: str) -> str:
    prompt = f"""Bạn là Trùm Copywriter chuyên viral content Facebook. Mệnh lệnh bắt buộc:
1. Viết lại caption sao cho kịch tính, thú vị, xài emoji hợp lý, độ dài 50-100 từ.
2. Ngay lập tức loại bỏ toàn bộ hashtag cũ trong caption gốc.
3. Dựa vào nội dung, tự bổ sung 5-6 hashtag phù hợp cho Facebook.
Kết quả chỉ trả về đoạn caption thuần túy, không có giải thích.

Caption gốc: {original_caption}"""
    return _generate_with_gemini(prompt, f"{original_caption}\n\n#giaitri #trending", timeout=30)


def generate_reply(user_message: str, *, channel: str = "comment", prompt_override: str | None = None) -> str:
    is_message_channel = channel == "message"
    base_prompt = (prompt_override or "").strip() or (
        DEFAULT_MESSAGE_REPLY_PROMPT if is_message_channel else DEFAULT_COMMENT_REPLY_PROMPT
    )
    customer_label = "Tin nhắn inbox" if is_message_channel else "Bình luận"
    fallback = "Cảm ơn bạn đã nhắn cho trang. Bên mình sẽ hỗ trợ bạn sớm nhé!"
    if not is_message_channel:
        fallback = "Cảm ơn bạn đã quan tâm nhé! 💖"

    prompt = (
        f"{base_prompt}\n\n"
        f"Ngữ cảnh hiện tại:\n"
        f"- Kênh: {customer_label}\n"
        f"- Trả lời ngắn gọn, đúng trọng tâm, không lặp ý.\n"
        f"- Không nhắc đến việc bạn là AI.\n\n"
        f"Khách hàng nhắn: {user_message}"
    )
    return _generate_with_gemini(prompt, fallback)
