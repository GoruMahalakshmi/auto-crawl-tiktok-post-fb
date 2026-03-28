from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Union
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import InteractionLog, FacebookPage, InteractionStatus
from app.services.ai_generator import generate_reply
from app.services.fb_graph import reply_to_comment
import os

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "social_auto_2026")

@router.get("/fb")
def verify_webhook(request: Request):
    """Xác thực Webhook với Facebook"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook Verified!")
        return PlainTextResponse(content=challenge) # Facebook Yêu cầu trả về raw challenge
    raise HTTPException(status_code=403, detail="Invalid verification token")

@router.post("/fb")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Nhận sự kiện Comment từ Facebook Webhook"""
    payload = await request.json()
    
    if payload.get("object") == "page":
        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            if "changes" in entry:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Xử lý Test Webhook từ Facebook Dashboard
                    if change.get("field") == "feed" and value.get("item") == "status" and value.get("message") == "Example post content.":
                        print(f"FB DEBUG: Nhận sự kiện Test từ Facebook Dashboard (Page ID: {page_id}). Kết nối ổn định!")
                        continue

                    # Xử lý comment add thực tế
                    if change.get("field") == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                        comment_id = value.get("comment_id")
                        message = value.get("message")
                        post_id = value.get("post_id")
                        sender_id = value.get("from", {}).get("id")

                        # Bỏ qua nếu là Page tự comment
                        if sender_id == page_id:
                            continue
                            
                        # Kiểm tra trùng lặp (Facebook webhooks có thể gửi 1 sự kiện nhiều lần)
                        existing = db.query(InteractionLog).filter(InteractionLog.comment_id == comment_id).first()
                        if existing:
                            continue
                            
                        # Kiểm tra xem Trang này có trong hệ thống không (để tránh lỗi Foreign Key)
                        page_config = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
                        if not page_config:
                            print(f"FB WARNING: Nhận bình luận từ Page ID lạ ({page_id}). Bỏ qua vì không có trong hệ thống.")
                            continue

                        log = InteractionLog(
                            page_id=page_id,
                            post_id=post_id,
                            comment_id=comment_id,
                            user_id=sender_id,
                            user_message=message,
                            status=InteractionStatus.pending
                        )
                        db.add(log)
                        db.commit()
                        
                        # AI Reply
                        page_config = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
                        if page_config and page_config.long_lived_access_token:
                            ai_reply = generate_reply(message)
                            log.ai_reply = ai_reply
                            
                            res = reply_to_comment(comment_id, ai_reply, page_config.long_lived_access_token)
                            if res and "id" in res:
                                log.status = InteractionStatus.replied
                            else:
                                log.status = InteractionStatus.failed
                            db.commit()
                            
    return {"status": "ok"}

@router.get("/logs")
def get_interaction_logs(db: Session = Depends(get_db)):
    """ Lấy danh sách nhật ký tự động trả lời bình luận """
    logs = db.query(InteractionLog).order_by(InteractionLog.status.desc()).limit(50).all()
    return logs
