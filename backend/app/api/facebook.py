from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models.models import FacebookPage
from app.services.observability import record_event
from app.services.security import decrypt_secret, encrypt_secret, is_secret_encrypted, mask_secret
from app.services.fb_graph import inspect_page_access, inspect_page_messenger_subscription, subscribe_page_to_app

router = APIRouter(prefix="/facebook", tags=["Trang Facebook"])
PAGE_WEBHOOK_REQUIRED_FIELDS = ("messages", "feed")

class FacebookPageCreate(BaseModel):
    page_id: str
    page_name: str
    long_lived_access_token: str


class FacebookAutomationUpdate(BaseModel):
    comment_auto_reply_enabled: bool
    comment_ai_prompt: str | None = None
    message_auto_reply_enabled: bool
    message_ai_prompt: str | None = None
    message_reply_schedule_enabled: bool = False
    message_reply_start_time: str = Field(default="08:00", pattern=r"^\d{2}:\d{2}$")
    message_reply_end_time: str = Field(default="22:00", pattern=r"^\d{2}:\d{2}$")
    message_reply_cooldown_minutes: int = Field(default=0, ge=0, le=1440)


def _normalize_time_string(value: str, *, field_name: str) -> str:
    raw = (value or "").strip()
    try:
        hours, minutes = raw.split(":")
        hour_value = int(hours)
        minute_value = int(minutes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} phải theo định dạng HH:MM.") from exc

    if not (0 <= hour_value <= 23 and 0 <= minute_value <= 59):
        raise HTTPException(status_code=400, detail=f"{field_name} không hợp lệ.")

    return f"{hour_value:02d}:{minute_value:02d}"

def get_token_kind(token: str | None) -> str:
    if not token:
        return "missing"
    try:
        plain_token = decrypt_secret(token)
    except ValueError:
        return "invalid_encryption"
    if plain_token.startswith("http://") or plain_token.startswith("https://"):
        return "legacy_webhook"
    return "page_access_token"


def _validate_page_access_token(page_id: str, access_token: str) -> dict:
    inspection = inspect_page_access(page_id, access_token)
    if inspection.get("ok"):
        return inspection

    raise HTTPException(
        status_code=400,
        detail=inspection.get("message", "Không thể xác minh Page Access Token."),
    )


def serialize_page_config(page: FacebookPage) -> dict:
    raw_token = page.long_lived_access_token
    if raw_token and not is_secret_encrypted(raw_token):
        page.long_lived_access_token = encrypt_secret(raw_token)
        raw_token = page.long_lived_access_token

    try:
        decrypted = decrypt_secret(raw_token)
        token_kind = get_token_kind(raw_token)
        token_preview = mask_secret(decrypted)
    except ValueError:
        token_kind = "invalid_encryption"
        token_preview = None

    return {
        "page_id": page.page_id,
        "page_name": page.page_name,
        "has_token": bool(raw_token),
        "token_kind": token_kind,
        "token_preview": token_preview,
        "token_is_encrypted": bool(raw_token and is_secret_encrypted(raw_token)),
        "comment_auto_reply_enabled": page.comment_auto_reply_enabled is not False,
        "comment_ai_prompt": page.comment_ai_prompt or "",
        "message_auto_reply_enabled": bool(page.message_auto_reply_enabled),
        "message_ai_prompt": page.message_ai_prompt or "",
        "message_reply_schedule_enabled": bool(page.message_reply_schedule_enabled),
        "message_reply_start_time": page.message_reply_start_time or "08:00",
        "message_reply_end_time": page.message_reply_end_time or "22:00",
        "message_reply_cooldown_minutes": page.message_reply_cooldown_minutes or 0,
    }

@router.post("/config")
def set_facebook_config(page_in: FacebookPageCreate, db: Session = Depends(get_db)):
    normalized_token = page_in.long_lived_access_token.strip()

    if get_token_kind(normalized_token) == "legacy_webhook":
        raise HTTPException(
            status_code=400,
            detail="Hãy nhập mã truy cập trang Facebook thật. Liên kết webhook cũ không còn dùng để đăng bài hoặc trả lời bình luận."
        )

    inspection = _validate_page_access_token(page_in.page_id, normalized_token)

    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_in.page_id).first()
    if page:
        page.page_name = page_in.page_name
        page.long_lived_access_token = encrypt_secret(normalized_token)
    else:
        page = FacebookPage(
            page_id=page_in.page_id,
            page_name=page_in.page_name,
            long_lived_access_token=encrypt_secret(normalized_token)
        )
        db.add(page)
    db.commit()
    record_event(
        "facebook",
        "info",
        "Đã lưu cấu hình trang Facebook.",
        db=db,
        details={
            "page_id": page_in.page_id,
            "page_name": page_in.page_name,
            "token_kind": inspection.get("token_kind"),
        },
    )
    return {
        "message": "Đã lưu Page Access Token thành công!",
        "page": serialize_page_config(page),
        "validation": inspection,
    }

@router.get("/config")
def get_facebook_config(db: Session = Depends(get_db)):
    pages = db.query(FacebookPage).all()
    should_commit = False
    normalized_pages = []

    for page in pages:
        before_token = page.long_lived_access_token
        payload = serialize_page_config(page)
        if page.long_lived_access_token != before_token:
            should_commit = True
        normalized_pages.append(payload)

    if should_commit:
        db.commit()

    return normalized_pages


@router.patch("/config/{page_id}/automation")
def update_facebook_automation(page_id: str, payload: FacebookAutomationUpdate, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy fanpage cần cập nhật.")

    page.comment_auto_reply_enabled = payload.comment_auto_reply_enabled
    page.comment_ai_prompt = (payload.comment_ai_prompt or "").strip() or None
    page.message_auto_reply_enabled = payload.message_auto_reply_enabled
    page.message_ai_prompt = (payload.message_ai_prompt or "").strip() or None
    page.message_reply_schedule_enabled = payload.message_reply_schedule_enabled
    page.message_reply_start_time = _normalize_time_string(payload.message_reply_start_time, field_name="Giờ bắt đầu")
    page.message_reply_end_time = _normalize_time_string(payload.message_reply_end_time, field_name="Giờ kết thúc")
    page.message_reply_cooldown_minutes = payload.message_reply_cooldown_minutes
    db.commit()
    db.refresh(page)

    record_event(
        "facebook",
        "info",
        "Đã cập nhật cấu hình AI theo fanpage.",
        db=db,
        details={
            "page_id": page.page_id,
            "comment_auto_reply_enabled": page.comment_auto_reply_enabled,
            "message_auto_reply_enabled": page.message_auto_reply_enabled,
            "message_reply_schedule_enabled": page.message_reply_schedule_enabled,
            "message_reply_start_time": page.message_reply_start_time,
            "message_reply_end_time": page.message_reply_end_time,
            "message_reply_cooldown_minutes": page.message_reply_cooldown_minutes,
        },
    )
    return {
        "message": f"Đã lưu cấu hình AI cho fanpage {page.page_name}.",
        "page": serialize_page_config(page),
    }


@router.get("/config/{page_id}/validate")
def validate_facebook_page(page_id: str, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang Facebook trong hệ thống.")

    if not page.long_lived_access_token:
        raise HTTPException(status_code=400, detail="Trang Facebook này chưa có mã truy cập để kiểm tra.")

    token_kind = get_token_kind(page.long_lived_access_token)
    if token_kind != "page_access_token":
        raise HTTPException(status_code=400, detail="Mã truy cập hiện tại không phải mã truy cập trang Facebook hợp lệ.")

    try:
        access_token = decrypt_secret(page.long_lived_access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = _validate_page_access_token(page.page_id, access_token)
    messenger_connection = inspect_page_messenger_subscription(
        page.page_id,
        access_token,
        required_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    record_event(
        "facebook",
        "info",
        "Đã xác minh mã truy cập trang Facebook.",
        db=db,
        details={
            "page_id": page.page_id,
            "page_name": page.page_name,
            "messenger_connected": messenger_connection.get("connected", False),
        },
    )
    return {
        **result,
        "messenger_connection": messenger_connection,
    }


@router.post("/config/{page_id}/subscribe-messages")
def subscribe_facebook_page_messages(page_id: str, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang Facebook trong hệ thống.")

    if not page.long_lived_access_token:
        raise HTTPException(status_code=400, detail="Trang Facebook này chưa có mã truy cập để đăng ký.")

    try:
        access_token = decrypt_secret(page.long_lived_access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    validation = _validate_page_access_token(page.page_id, access_token)
    subscription = subscribe_page_to_app(
        page.page_id,
        access_token,
        subscribed_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    if not subscription.get("ok"):
        raise HTTPException(status_code=400, detail=subscription.get("message", "Không thể đăng ký fanpage nhận tin nhắn."))

    messenger_connection = inspect_page_messenger_subscription(
        page.page_id,
        access_token,
        required_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    record_event(
        "facebook",
        "info",
        "Đã đăng ký fanpage nhận webhook tin nhắn.",
        db=db,
        details={
            "page_id": page.page_id,
            "page_name": page.page_name,
            "messenger_connected": messenger_connection.get("connected", False),
            "required_fields": messenger_connection.get("required_fields", []),
        },
    )
    return {
        "message": "Đã đăng ký fanpage nhận webhook messages và feed cho app hiện tại.",
        "page": serialize_page_config(page),
        "validation": validation,
        "messenger_connection": messenger_connection,
    }
