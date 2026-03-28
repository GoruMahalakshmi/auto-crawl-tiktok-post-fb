import os

class Settings:
    PROJECT_NAME: str = "Social Automation API"
    # Dùng host là db (tên service trong docker-compose) 
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@db/social_auto")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000") # Cần đổi khi lên server

settings = Settings()
