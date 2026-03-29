from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.core.config import DEFAULT_JWT_SECRET, DEFAULT_TOKEN_ENCRYPTION_SECRET, settings
from app.core.database import get_db
from app.models.models import (
    Campaign,
    CampaignStatus,
    FacebookPage,
    InboxMessageLog,
    InteractionLog,
    InteractionStatus,
    SystemEvent,
    TaskQueue,
    TaskStatus,
    User,
    Video,
    VideoStatus,
    WorkerHeartbeat,
)
from app.services.observability import record_event
from app.services.runtime_settings import (
    build_runtime_settings_payload,
    get_runtime_setting_specs,
    resolve_runtime_value,
    update_runtime_settings,
)
from app.services.security import is_default_secret
from app.services.task_queue import serialize_task, summarize_tasks

router = APIRouter(prefix="/system", tags=["Hệ thống"])


class RuntimeSettingsUpdateRequest(BaseModel):
    BASE_URL: str | None = Field(default=None)
    FB_VERIFY_TOKEN: str | None = Field(default=None)
    FB_APP_SECRET: str | None = Field(default=None)
    GEMINI_API_KEY: str | None = Field(default=None)
    TUNNEL_TOKEN: str | None = Field(default=None)


def serialize_worker(worker: WorkerHeartbeat) -> dict:
    now = datetime.utcnow()
    age_seconds = int((now - worker.last_seen_at).total_seconds()) if worker.last_seen_at else None
    is_online = bool(age_seconds is not None and age_seconds <= settings.WORKER_STALE_SECONDS)
    return {
        "worker_name": worker.worker_name,
        "app_role": worker.app_role,
        "hostname": worker.hostname,
        "status": worker.status,
        "current_task_id": worker.current_task_id,
        "current_task_type": worker.current_task_type,
        "details": worker.details or {},
        "last_seen_at": worker.last_seen_at.isoformat() if worker.last_seen_at else None,
        "age_seconds": age_seconds,
        "is_online": is_online,
    }


def serialize_event(event: SystemEvent) -> dict:
    return {
        "id": str(event.id),
        "scope": event.scope,
        "level": event.level,
        "message": event.message,
        "details": event.details or {},
        "actor_user_id": event.actor_user_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/overview")
def get_system_overview(db: Session = Depends(get_db)):
    base_url = resolve_runtime_value("BASE_URL", db=db).rstrip("/")
    webhook_url = f"{base_url}/webhooks/fb" if base_url else None
    verify_token = resolve_runtime_value("FB_VERIFY_TOKEN", db=db)
    fb_app_secret = resolve_runtime_value("FB_APP_SECRET", db=db)
    tunnel_token = resolve_runtime_value("TUNNEL_TOKEN", db=db)
    warnings = []
    worker_cutoff = datetime.utcnow() - timedelta(seconds=settings.WORKER_STALE_SECONDS)

    if not webhook_url or not webhook_url.startswith("https://"):
        warnings.append("BASE_URL chưa là HTTPS công khai. Facebook webhook sẽ không hoạt động ổn định.")
    if is_default_secret(settings.JWT_SECRET, DEFAULT_JWT_SECRET):
        warnings.append("JWT_SECRET đang dùng giá trị mặc định.")
    if is_default_secret(settings.TOKEN_ENCRYPTION_SECRET, DEFAULT_TOKEN_ENCRYPTION_SECRET):
        warnings.append("TOKEN_ENCRYPTION_SECRET đang dùng giá trị mặc định.")
    if not fb_app_secret:
        warnings.append("Chưa cấu hình FB_APP_SECRET nên chưa xác minh chữ ký webhook.")
    if not tunnel_token:
        warnings.append("Chưa cấu hình TUNNEL_TOKEN nên tunnel chưa thể tự kết nối.")

    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    online_workers = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.last_seen_at >= worker_cutoff).count()
    queue_summary = summarize_tasks(db)
    must_change_password = db.query(User).filter(User.must_change_password.is_(True)).count()
    pending_comment_replies = db.query(InteractionLog).filter(InteractionLog.status == InteractionStatus.pending).count()
    pending_message_replies = db.query(InboxMessageLog).filter(InboxMessageLog.status == InteractionStatus.pending).count()

    if must_change_password:
        warnings.append("Có tài khoản đang bị yêu cầu đổi mật khẩu.")
    if queue_summary.get(TaskStatus.failed.value, 0):
        warnings.append("Có tác vụ nền đã thất bại và cần kiểm tra.")

    return {
        "project_name": settings.PROJECT_NAME,
        "server_time": datetime.utcnow().isoformat(),
        "app_role": settings.APP_ROLE,
        "base_url": base_url,
        "webhook_url": webhook_url,
        "verify_token": verify_token,
        "public_webhook_ready": bool(webhook_url and webhook_url.startswith("https://")),
        "webhook_signature_enabled": bool(fb_app_secret),
        "tunnel_token_configured": bool(tunnel_token),
        "background_jobs_mode": settings.BACKGROUND_JOBS_MODE,
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "scheduler_interval_minutes": settings.SCHEDULER_INTERVAL_MINUTES,
        "connected_pages": db.query(FacebookPage).count(),
        "active_campaigns": db.query(Campaign).filter(Campaign.status == CampaignStatus.active).count(),
        "paused_campaigns": db.query(Campaign).filter(Campaign.status == CampaignStatus.paused).count(),
        "queue_ready": db.query(Video).filter(Video.status == VideoStatus.ready).count(),
        "pending_comment_replies": pending_comment_replies,
        "pending_message_replies": pending_message_replies,
        "pending_replies": pending_comment_replies + pending_message_replies,
        "message_auto_reply_pages": db.query(FacebookPage).filter(FacebookPage.message_auto_reply_enabled.is_(True)).count(),
        "active_users": active_users,
        "online_workers": online_workers,
        "must_change_password_users": must_change_password,
        "task_queue": queue_summary,
        "warnings": warnings,
    }


@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    db_ok = True
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    base_url = resolve_runtime_value("BASE_URL", db=db).rstrip("/")
    tunnel_token = resolve_runtime_value("TUNNEL_TOKEN", db=db)
    fb_app_secret = resolve_runtime_value("FB_APP_SECRET", db=db)
    workers = [serialize_worker(worker) for worker in db.query(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc()).all()]
    queue_summary = summarize_tasks(db)

    return {
        "checked_at": datetime.utcnow().isoformat(),
        "database": {"ok": db_ok, "error": db_error},
        "worker": {
            "expected_mode": settings.BACKGROUND_JOBS_MODE,
            "online_count": sum(1 for worker in workers if worker["is_online"]),
            "workers": workers,
        },
        "queue": queue_summary,
        "config": {
            "public_webhook_ready": bool(base_url.startswith("https://")),
            "webhook_signature_enabled": bool(fb_app_secret),
            "tunnel_token_configured": bool(tunnel_token),
            "scheduler_enabled": settings.SCHEDULER_ENABLED,
            "task_queue_poll_seconds": settings.TASK_QUEUE_POLL_SECONDS,
        },
    }


@router.get("/runtime-config")
def get_runtime_config(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return build_runtime_settings_payload(db)


@router.put("/runtime-config")
def save_runtime_config(
    payload: RuntimeSettingsUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    changed_keys = update_runtime_settings(
        db,
        payload.model_dump(),
        actor_user_id=str(current_user.id),
    )
    response_payload = build_runtime_settings_payload(db)
    restart_required_keys = [
        key
        for key in changed_keys
        if get_runtime_setting_specs()[key]["requires_restart"]
    ]

    if changed_keys:
        record_event(
            "system",
            "info",
            "Đã cập nhật cấu hình runtime từ dashboard.",
            db=db,
            actor_user_id=str(current_user.id),
            details={"changed_keys": changed_keys, "restart_required_keys": restart_required_keys},
        )

    message = "Không có thay đổi nào được lưu."
    if changed_keys:
        message = "Đã lưu cấu hình runtime."
        if restart_required_keys:
            message += " Một số mục cần khởi động lại service liên quan để áp dụng."

    response_payload["changed_keys"] = changed_keys
    response_payload["restart_required_keys"] = restart_required_keys
    response_payload["message"] = message
    return response_payload


@router.get("/tasks")
def get_tasks(limit: int = 20, db: Session = Depends(get_db)):
    tasks = db.query(TaskQueue).order_by(TaskQueue.created_at.desc()).limit(min(max(limit, 1), 100)).all()
    return {"tasks": [serialize_task(task) for task in tasks], "summary": summarize_tasks(db)}


@router.get("/events")
def get_events(limit: int = 30, db: Session = Depends(get_db)):
    events = db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(min(max(limit, 1), 200)).all()
    return {"events": [serialize_event(event) for event in events]}


@router.get("/workers")
def get_workers(db: Session = Depends(get_db)):
    workers = db.query(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc()).all()
    return {"workers": [serialize_worker(worker) for worker in workers]}


@router.post("/workers/cleanup")
def cleanup_stale_workers(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stale_cutoff = datetime.utcnow() - timedelta(seconds=settings.WORKER_STALE_SECONDS)
    stale_workers = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.last_seen_at < stale_cutoff).all()
    stale_names = [worker.worker_name for worker in stale_workers]

    if not stale_workers:
        return {"deleted_count": 0, "deleted_workers": [], "message": "Không có worker mất kết nối nào để dọn."}

    deleted_count = len(stale_workers)
    for worker in stale_workers:
        db.delete(worker)
    db.commit()

    record_event(
        "worker",
        "info",
        "Đã dọn các worker mất kết nối khỏi bảng heartbeat.",
        db=db,
        actor_user_id=str(current_user.id),
        details={"deleted_count": deleted_count, "deleted_workers": stale_names},
    )

    return {
        "deleted_count": deleted_count,
        "deleted_workers": stale_names,
        "message": f"Đã dọn {deleted_count} worker mất kết nối.",
    }
