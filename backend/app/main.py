from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.models import models
from app.api import campaigns, facebook, webhooks
from app.worker.cron import start_scheduler

import time
from sqlalchemy.exc import OperationalError

# Thử lại kết nối Database cho đến khi thành công (tránh lỗi race condition khi khởi động Docker)
max_retries = 10
retry_count = 0
while retry_count < max_retries:
    try:
        print(f"Hệ thống: Đang kết nối Database (Lần {retry_count + 1}/{max_retries})...")
        Base.metadata.create_all(bind=engine)
        print("Hệ thống: Kết nối Database thành công!")
        break
    except OperationalError:
        retry_count += 1
        if retry_count == max_retries:
            print("Hệ thống: Lỗi nghiêm trọng - Không thể kết nối Database sau nhiều lần thử.")
            raise
        print("Hệ thống: Database chưa sẵn sàng, đang đợi 5 giây...")
        time.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Khởi động Background Scheduler...")
    start_scheduler()
    yield

app = FastAPI(title="Social Automation API", lifespan=lifespan)

from fastapi import Depends
from app.api.auth import verify_token
from app.api import auth

app.include_router(auth.router)
app.include_router(campaigns.router, dependencies=[Depends(verify_token)])
app.include_router(facebook.router, dependencies=[Depends(verify_token)])
app.include_router(webhooks.router)

# Phục vụ file tĩnh cho folder downloads (để Make.com tải về)
app.mount("/downloads", StaticFiles(directory="/app/downloads"), name="downloads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Social Automation API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
