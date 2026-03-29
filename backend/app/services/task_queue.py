from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import TaskQueue, TaskStatus

TASK_TYPE_CAMPAIGN_SYNC = "campaign_sync"
TASK_TYPE_VIDEO_RETRY = "video_retry"
TASK_TYPE_COMMENT_REPLY = "comment_reply"
TASK_TYPE_MESSAGE_REPLY = "message_reply"


def normalize_task_status(value):
    return value.value if hasattr(value, "value") else value


def serialize_task(task: TaskQueue) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "entity_type": task.entity_type,
        "entity_id": task.entity_id,
        "status": normalize_task_status(task.status),
        "priority": task.priority,
        "attempts": task.attempts,
        "max_attempts": task.max_attempts,
        "last_error": task.last_error,
        "locked_by": task.locked_by,
        "payload": task.payload or {},
        "available_at": task.available_at.isoformat() if task.available_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def get_open_task(
    db: Session,
    *,
    task_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> TaskQueue | None:
    query = db.query(TaskQueue).filter(
        TaskQueue.task_type == task_type,
        TaskQueue.status.in_([TaskStatus.queued, TaskStatus.processing]),
    )
    if entity_type:
        query = query.filter(TaskQueue.entity_type == entity_type)
    if entity_id:
        query = query.filter(TaskQueue.entity_id == entity_id)
    return query.order_by(TaskQueue.created_at.asc()).first()


def enqueue_task(
    db: Session,
    *,
    task_type: str,
    payload: dict[str, Any],
    entity_type: str | None = None,
    entity_id: str | None = None,
    priority: int = 0,
    max_attempts: int = 3,
    available_at: datetime | None = None,
    dedupe_open_task: bool = True,
) -> TaskQueue:
    if dedupe_open_task:
        existing = get_open_task(
            db,
            task_type=task_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if existing:
            return existing

    task = TaskQueue(
        task_type=task_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        priority=priority,
        max_attempts=max_attempts,
        available_at=available_at or datetime.utcnow(),
        status=TaskStatus.queued,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def claim_next_task(db: Session, worker_name: str) -> TaskQueue | None:
    now = datetime.utcnow()
    task = (
        db.query(TaskQueue)
        .filter(
            TaskQueue.status == TaskStatus.queued,
            or_(TaskQueue.available_at.is_(None), TaskQueue.available_at <= now),
        )
        .order_by(TaskQueue.priority.desc(), TaskQueue.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not task:
        return None

    task.status = TaskStatus.processing
    task.attempts = (task.attempts or 0) + 1
    task.locked_at = now
    task.locked_by = worker_name
    task.started_at = now
    task.last_error = None
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task: TaskQueue) -> TaskQueue:
    task.status = TaskStatus.completed
    task.completed_at = datetime.utcnow()
    task.locked_at = None
    task.locked_by = None
    db.commit()
    db.refresh(task)
    return task


def fail_task(db: Session, task: TaskQueue, error_message: str, *, retry_delay_seconds: int | None = None) -> TaskQueue:
    task.last_error = error_message[:1000]
    task.locked_at = None
    task.locked_by = None
    task.completed_at = None

    if (task.attempts or 0) < (task.max_attempts or 1):
        delay_seconds = retry_delay_seconds if retry_delay_seconds is not None else min(300, max(5, task.attempts * 15))
        task.status = TaskStatus.queued
        task.available_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    else:
        task.status = TaskStatus.failed
        task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task


def summarize_tasks(db: Session) -> dict[str, int]:
    rows = db.query(TaskQueue.status, func.count(TaskQueue.id)).group_by(TaskQueue.status).all()
    summary = {status.value: 0 for status in TaskStatus}
    for status, count in rows:
        summary[normalize_task_status(status)] = count
    return summary
