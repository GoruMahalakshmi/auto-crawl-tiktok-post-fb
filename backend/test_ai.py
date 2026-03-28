import sys
import os

# Đường dẫn đang xét (cwd) sẽ là root của backend bên trong docker (/app)
sys.path.insert(0, '.')

from app.core.config import settings
from app.services.ai_generator import generate_caption

print(f"API Key Load Status: {'SUCCESS' if settings.GEMINI_API_KEY else 'FAILED (No Key found)'}")

try:
    print("----- GỬI REQUEST LÊN OPENAI -----")
    result = generate_caption("Hôm nay view triệu đô xịn quá nha anh em ơiii! nhớ ghé thử quán Chill nha! #tiktok #xuhuong #fyp #douyin #foryou")
    print("----- KẾT QUẢ TỪ AI -----")
    print(result)
    print("-------------------------")
except Exception as e:
    print(f"Error occurred: {e}")
