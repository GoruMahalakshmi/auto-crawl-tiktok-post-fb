import json
from datetime import datetime, timedelta
from json import JSONDecodeError
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.auth import require_authenticated_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import FacebookPage, InboxMessageLog, InteractionLog, InteractionStatus, User
from app.services.observability import record_event
from app.services.runtime_settings import resolve_runtime_value
from app.services.security import verify_facebook_signature
from app.services.task_queue import TASK_TYPE_COMMENT_REPLY, TASK_TYPE_MESSAGE_REPLY, enqueue_task

router = APIRouter(prefix="/webhooks", tags=["Webhook"])
LOCAL_TIMEZONE = ZoneInfo(settings.APP_TIMEZONE)


def serialize_interaction_log(log: InteractionLog) -> dict:
    return {
        "id": str(log.id),
        "page_id": log.page_id,
        "post_id": log.post_id,
        "comment_id": log.comment_id,
        "user_id": log.user_id,
        "user_message": log.user_message,
        "ai_reply": log.ai_reply,
        "status": log.status.value if hasattr(log.status, "value") else log.status,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "updated_at": log.updated_at.isoformat() if log.updated_at else None,
    }


def serialize_message_log(log: InboxMessageLog) -> dict:
    return {
        "id": str(log.id),
        "page_id": log.page_id,
        "facebook_message_id": log.facebook_message_id,
        "sender_id": log.sender_id,
        "recipient_id": log.recipient_id,
        "user_message": log.user_message,
        "ai_reply": log.ai_reply,
        "facebook_reply_message_id": log.facebook_reply_message_id,
        "last_error": log.last_error,
        "status": log.status.value if hasattr(log.status, "value") else log.status,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "updated_at": log.updated_at.isoformat() if log.updated_at else None,
    }


def get_local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def _parse_hhmm(raw_value: str | None):
    value = (raw_value or "").strip()
    try:
        hours, minutes = value.split(":")
        return int(hours), int(minutes)
    except Exception:
        return None


def _is_within_message_schedule(page_config: FacebookPage, local_now: datetime) -> tuple[bool, str | None]:
    if not page_config.message_reply_schedule_enabled:
        return True, None

    start_parts = _parse_hhmm(page_config.message_reply_start_time)
    end_parts = _parse_hhmm(page_config.message_reply_end_time)
    if not start_parts or not end_parts:
        return True, None

    current_minutes = local_now.hour * 60 + local_now.minute
    start_minutes = start_parts[0] * 60 + start_parts[1]
    end_minutes = end_parts[0] * 60 + end_parts[1]

    if start_minutes == end_minutes:
        return True, None

    if start_minutes < end_minutes:
        is_allowed = start_minutes <= current_minutes < end_minutes
    else:
        is_allowed = current_minutes >= start_minutes or current_minutes < end_minutes

    if is_allowed:
        return True, None

    return False, f"Ngoài khung giờ tự động phản hồi {page_config.message_reply_start_time}-{page_config.message_reply_end_time}."


def _get_message_cooldown_reason(db: Session, page_id: str, sender_id: str, cooldown_minutes: int) -> str | None:
    if cooldown_minutes <= 0:
        return None

    latest_log = (
        db.query(InboxMessageLog)
        .filter(
            InboxMessageLog.page_id == page_id,
            InboxMessageLog.sender_id == sender_id,
            InboxMessageLog.status.in_([InteractionStatus.pending, InteractionStatus.replied]),
        )
        .order_by(InboxMessageLog.updated_at.desc(), InboxMessageLog.created_at.desc())
        .first()
    )
    if not latest_log:
        return None

    latest_time = latest_log.updated_at or latest_log.created_at
    if not latest_time:
        return None

    if latest_time >= datetime.utcnow() - timedelta(minutes=cooldown_minutes):
        return f"Đang trong thời gian chờ {cooldown_minutes} phút cho người gửi này."

    return None


def _record_comment_event(db: Session, page_id: str, value: dict):
    comment_id = value.get("comment_id")
    message = value.get("message")
    post_id = value.get("post_id")
    sender_id = value.get("from", {}).get("id")

    if sender_id == page_id:
        return

    existing = db.query(InteractionLog).filter(InteractionLog.comment_id == comment_id).first()
    if existing:
        return

    page_config = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page_config:
        record_event(
            "webhook",
            "warning",
            "Nhận bình luận từ trang chưa cấu hình.",
            db=db,
            details={"page_id": page_id, "comment_id": comment_id},
        )
        return

    comment_auto_reply_enabled = page_config.comment_auto_reply_enabled is not False

    log = InteractionLog(
        page_id=page_id,
        post_id=post_id,
        comment_id=comment_id,
        user_id=sender_id,
        user_message=message,
        status=InteractionStatus.pending if comment_auto_reply_enabled else InteractionStatus.ignored,
    )
    if not comment_auto_reply_enabled:
        log.ai_reply = "Tự động phản hồi bình luận đang tắt cho fanpage này."
    db.add(log)
    db.commit()
    db.refresh(log)

    if not comment_auto_reply_enabled:
        record_event(
            "webhook",
            "info",
            "Đã ghi nhận bình luận mới nhưng không tự động phản hồi vì fanpage đang tắt chế độ này.",
            db=db,
            details={"comment_id": comment_id, "page_id": page_id},
        )
        return

    task = enqueue_task(
        db,
        task_type=TASK_TYPE_COMMENT_REPLY,
        entity_type="interaction_log",
        entity_id=str(log.id),
        payload={"interaction_log_id": str(log.id)},
        priority=10,
        max_attempts=3,
    )
    record_event(
        "webhook",
        "info",
        "Đã ghi nhận bình luận mới và đưa vào hàng đợi phản hồi.",
        db=db,
        details={"comment_id": comment_id, "page_id": page_id, "task_id": str(task.id)},
    )


def _record_message_event(db: Session, page_id: str, event: dict):
    sender_id = event.get("sender", {}).get("id")
    recipient_id = event.get("recipient", {}).get("id")
    message = event.get("message") or {}
    message_id = message.get("mid")
    text = (message.get("text") or "").strip()

    if not sender_id or sender_id == page_id or message.get("is_echo") or not text or not message_id:
        return

    existing = db.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == message_id).first()
    if existing:
        return

    page_config = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page_config:
        record_event(
            "webhook",
            "warning",
            "Nhận tin nhắn inbox từ trang chưa cấu hình.",
            db=db,
            details={"page_id": page_id, "message_id": message_id},
        )
        return

    local_now = get_local_now()
    schedule_allowed, schedule_reason = _is_within_message_schedule(page_config, local_now)
    cooldown_reason = _get_message_cooldown_reason(
        db,
        page_id=page_id,
        sender_id=sender_id,
        cooldown_minutes=page_config.message_reply_cooldown_minutes or 0,
    )
    should_auto_reply = bool(page_config.message_auto_reply_enabled and schedule_allowed and not cooldown_reason)
    ignored_reason = None
    if not page_config.message_auto_reply_enabled:
        ignored_reason = "Tự động phản hồi inbox đang tắt cho fanpage này."
    elif not schedule_allowed:
        ignored_reason = schedule_reason
    elif cooldown_reason:
        ignored_reason = cooldown_reason

    log = InboxMessageLog(
        page_id=page_id,
        facebook_message_id=message_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        user_message=text,
        status=InteractionStatus.pending if should_auto_reply else InteractionStatus.ignored,
        ai_reply=None if should_auto_reply else ignored_reason,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    if not should_auto_reply:
        record_event(
            "webhook",
            "info",
            "Đã ghi nhận tin nhắn inbox mới nhưng không đưa vào tự động phản hồi.",
            db=db,
            details={
                "page_id": page_id,
                "message_id": message_id,
                "sender_id": sender_id,
                "reason": ignored_reason,
                "local_time": local_now.isoformat(),
            },
        )
        return

    task = enqueue_task(
        db,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(log.id),
        payload={"message_log_id": str(log.id)},
        priority=15,
        max_attempts=3,
    )
    record_event(
        "webhook",
        "info",
        "Đã ghi nhận tin nhắn inbox mới và đưa vào hàng đợi phản hồi.",
        db=db,
        details={"page_id": page_id, "message_id": message_id, "sender_id": sender_id, "task_id": str(task.id)},
    )


@router.get("/fb")
def verify_webhook(request: Request, db: Session = Depends(get_db)):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    verify_token = resolve_runtime_value("FB_VERIFY_TOKEN", db=db)

    if mode == "subscribe" and token == verify_token:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Mã xác minh webhook không hợp lệ")


@router.post("/fb")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    app_secret = resolve_runtime_value("FB_APP_SECRET", db=db)
    if app_secret and not verify_facebook_signature(body, signature, app_secret=app_secret):
        raise HTTPException(status_code=403, detail="Chữ ký webhook không hợp lệ")

    try:
        payload = json.loads(body.decode("utf-8"))
    except JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Dữ liệu webhook không phải JSON hợp lệ.") from exc

    if payload.get("object") == "page":
        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            for event in entry.get("messaging", []):
                _record_message_event(db, page_id, event)
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if change.get("field") == "feed" and value.get("item") == "status" and value.get("message") == "Example post content.":
                    record_event(
                        "webhook",
                        "info",
                        "Đã nhận sự kiện thử webhook từ Facebook.",
                        db=db,
                        details={"page_id": page_id},
                    )
                    continue

                if change.get("field") == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                    _record_comment_event(db, page_id, value)

    return {"status": "đã nhận"}


@router.get("/logs")
def get_interaction_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    logs = db.query(InteractionLog).order_by(InteractionLog.created_at.desc()).limit(50).all()
    return [serialize_interaction_log(log) for log in logs]


@router.get("/messages")
def get_message_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    logs = db.query(InboxMessageLog).order_by(InboxMessageLog.created_at.desc()).limit(50).all()
    return [serialize_message_log(log) for log in logs]
