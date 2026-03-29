from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.models import FacebookPage, InboxMessageLog, InteractionStatus, TaskQueue
from app.services.security import encrypt_secret
from app.services.task_queue import TASK_TYPE_MESSAGE_REPLY, enqueue_task
from app.worker.tasks import process_task_queue


def mock_page_access(page_id: str, access_token: str):
    return {
        "ok": True,
        "message": "Mã truy cập hợp lệ.",
        "token_kind": "page_access_token",
        "token_subject_id": page_id,
        "token_subject_name": "Trang demo",
        "page_id": page_id,
        "page_name": "Trang demo",
        "page_link": "https://facebook.com/demo-page",
        "fan_count": 123,
    }


def test_can_save_page_automation_settings(client, auth_headers, monkeypatch):
    from app.api import facebook as facebook_api

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)

    create_response = client.post(
        "/facebook/config",
        headers=auth_headers,
        json={
            "page_id": "page-1",
            "page_name": "Trang demo",
            "long_lived_access_token": "page-token-123456",
        },
    )
    assert create_response.status_code == 200

    update_response = client.patch(
        "/facebook/config/page-1/automation",
        headers=auth_headers,
        json={
            "comment_auto_reply_enabled": True,
            "comment_ai_prompt": "Trả lời bình luận thật vui vẻ.",
            "message_auto_reply_enabled": True,
            "message_ai_prompt": "Trả lời inbox như tư vấn viên bán hàng.",
            "message_reply_schedule_enabled": True,
            "message_reply_start_time": "08:30",
            "message_reply_end_time": "21:45",
            "message_reply_cooldown_minutes": 15,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["page"]["comment_ai_prompt"] == "Trả lời bình luận thật vui vẻ."
    assert payload["page"]["message_auto_reply_enabled"] is True
    assert payload["page"]["message_ai_prompt"] == "Trả lời inbox như tư vấn viên bán hàng."
    assert payload["page"]["message_reply_schedule_enabled"] is True
    assert payload["page"]["message_reply_start_time"] == "08:30"
    assert payload["page"]["message_reply_end_time"] == "21:45"
    assert payload["page"]["message_reply_cooldown_minutes"] == 15

    config_response = client.get("/facebook/config", headers=auth_headers)
    assert config_response.status_code == 200
    page_payload = config_response.json()[0]
    assert page_payload["comment_auto_reply_enabled"] is True
    assert page_payload["message_auto_reply_enabled"] is True
    assert page_payload["message_reply_schedule_enabled"] is True
    assert page_payload["message_reply_cooldown_minutes"] == 15


def test_rejects_user_access_token_when_saving_page(client, auth_headers, monkeypatch):
    from app.api import facebook as facebook_api

    monkeypatch.setattr(
        facebook_api,
        "inspect_page_access",
        lambda page_id, access_token: {
            "ok": False,
            "message": "Mã truy cập hiện tại là User Access Token. Hãy dùng đúng Page Access Token của fanpage.",
            "token_kind": "user_access_token",
            "token_subject_id": "user-1",
            "token_subject_name": "Người dùng thử nghiệm",
            "page_id": page_id,
            "page_name": "Trang demo",
        },
    )

    create_response = client.post(
        "/facebook/config",
        headers=auth_headers,
        json={
            "page_id": "page-user-token",
            "page_name": "Trang sai token",
            "long_lived_access_token": "user-token-123456",
        },
    )
    assert create_response.status_code == 400
    assert "User Access Token" in create_response.json()["detail"]


def test_validate_page_returns_messenger_connection(client, auth_headers, db_session, monkeypatch):
    from app.api import facebook as facebook_api

    page = FacebookPage(
        page_id="page-validate",
        page_name="Trang kiểm tra",
        long_lived_access_token=encrypt_secret("page-token-validate"),
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)
    monkeypatch.setattr(
        facebook_api,
        "inspect_page_messenger_subscription",
        lambda page_id, access_token, required_fields=("messages",): {
            "ok": True,
            "connected": True,
            "message": "Inbox đã kết nối với app kiểm thử.",
            "required_fields": list(required_fields),
            "connected_app": {
                "id": "app-1",
                "name": "Ứng dụng kiểm thử",
                "subscribed_fields": ["messages"],
            },
            "apps": [
                {
                    "id": "app-1",
                    "name": "Ứng dụng kiểm thử",
                    "subscribed_fields": ["messages"],
                }
            ],
        },
    )

    response = client.get("/facebook/config/page-validate/validate", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["token_kind"] == "page_access_token"
    assert payload["messenger_connection"]["connected"] is True
    assert payload["messenger_connection"]["connected_app"]["id"] == "app-1"


def test_can_subscribe_page_messages_from_dashboard(client, auth_headers, db_session, monkeypatch):
    from app.api import facebook as facebook_api

    page = FacebookPage(
        page_id="page-subscribe",
        page_name="Trang subscribe",
        long_lived_access_token=encrypt_secret("page-token-subscribe"),
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)
    monkeypatch.setattr(
        facebook_api,
        "subscribe_page_to_app",
        lambda page_id, access_token, subscribed_fields=("messages",): {
            "ok": True,
            "message": "Đã đăng ký messages.",
            "data": {"success": True},
        },
    )
    monkeypatch.setattr(
        facebook_api,
        "inspect_page_messenger_subscription",
        lambda page_id, access_token, required_fields=("messages",): {
            "ok": True,
            "connected": True,
            "message": "Inbox đã kết nối với app kiểm thử.",
            "required_fields": list(required_fields),
            "connected_app": {
                "id": "app-2",
                "name": "Ứng dụng kiểm thử",
                "subscribed_fields": ["messages"],
            },
            "apps": [
                {
                    "id": "app-2",
                    "name": "Ứng dụng kiểm thử",
                    "subscribed_fields": ["messages"],
                }
            ],
        },
    )

    response = client.post("/facebook/config/page-subscribe/subscribe-messages", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert "messages" in payload["message"]
    assert payload["validation"]["token_kind"] == "page_access_token"
    assert payload["messenger_connection"]["connected"] is True
    assert payload["messenger_connection"]["connected_app"]["id"] == "app-2"


def test_webhook_message_event_creates_message_log_and_task_when_enabled(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-enabled",
        page_name="Trang bật inbox",
        long_lived_access_token=encrypt_secret("page-token-enabled"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-enabled",
                    "messaging": [
                        {
                            "sender": {"id": "user-100"},
                            "recipient": {"id": "page-enabled"},
                            "message": {"mid": "mid.100", "text": "Xin chào shop"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    logs = db_session.query(InboxMessageLog).all()
    assert len(logs) == 1
    assert logs[0].status == InteractionStatus.pending
    assert logs[0].user_message == "Xin chào shop"

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert len(tasks) == 1
    assert tasks[0].entity_type == "inbox_message_log"


def test_webhook_message_event_is_recorded_without_task_when_disabled(client, db_session):
    page = FacebookPage(
        page_id="page-disabled",
        page_name="Trang tắt inbox",
        long_lived_access_token=encrypt_secret("page-token-disabled"),
        message_auto_reply_enabled=False,
    )
    db_session.add(page)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-disabled",
                    "messaging": [
                        {
                            "sender": {"id": "user-200"},
                            "recipient": {"id": "page-disabled"},
                            "message": {"mid": "mid.200", "text": "Có ai hỗ trợ không?"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    logs = db_session.query(InboxMessageLog).all()
    assert len(logs) == 1
    assert logs[0].status == InteractionStatus.ignored
    assert "đang tắt" in (logs[0].ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_webhook_message_event_is_ignored_outside_schedule(client, db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-schedule",
        page_name="Trang theo giờ",
        long_lived_access_token=encrypt_secret("page-token-schedule"),
        message_auto_reply_enabled=True,
        message_reply_schedule_enabled=True,
        message_reply_start_time="08:00",
        message_reply_end_time="17:00",
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(
        "app.api.webhooks.get_local_now",
        lambda: datetime(2026, 3, 29, 22, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
    )

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-schedule",
                    "messaging": [
                        {
                            "sender": {"id": "user-300"},
                            "recipient": {"id": "page-schedule"},
                            "message": {"mid": "mid.300", "text": "Nhắn ngoài giờ"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.300").first()
    assert log is not None
    assert log.status == InteractionStatus.ignored
    assert "Ngoài khung giờ" in (log.ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_webhook_message_event_is_ignored_during_cooldown(client, db_session):
    page = FacebookPage(
        page_id="page-cooldown",
        page_name="Trang cooldown",
        long_lived_access_token=encrypt_secret("page-token-cooldown"),
        message_auto_reply_enabled=True,
        message_reply_cooldown_minutes=30,
    )
    db_session.add(page)
    db_session.commit()

    previous_log = InboxMessageLog(
        page_id="page-cooldown",
        facebook_message_id="mid.old",
        sender_id="user-400",
        recipient_id="page-cooldown",
        user_message="Tin cũ",
        ai_reply="Đã phản hồi trước đó",
        status=InteractionStatus.replied,
    )
    db_session.add(previous_log)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-cooldown",
                    "messaging": [
                        {
                            "sender": {"id": "user-400"},
                            "recipient": {"id": "page-cooldown"},
                            "message": {"mid": "mid.400", "text": "Nhắn liên tiếp"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.400").first()
    assert log is not None
    assert log.status == InteractionStatus.ignored
    assert "thời gian chờ 30 phút" in (log.ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_worker_processes_message_reply_task(db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-worker",
        page_name="Trang worker",
        long_lived_access_token=encrypt_secret("page-token-worker"),
        message_auto_reply_enabled=True,
        message_ai_prompt="Tư vấn nhanh gọn.",
    )
    db_session.add(page)
    db_session.commit()

    log = InboxMessageLog(
        page_id="page-worker",
        facebook_message_id="mid.worker.1",
        sender_id="user-worker",
        recipient_id="page-worker",
        user_message="Cho mình xin giá",
        status=InteractionStatus.pending,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(log.id),
        payload={"message_log_id": str(log.id)},
        priority=20,
    )

    monkeypatch.setattr(
        "app.services.campaign_jobs.generate_reply",
        lambda user_message, **kwargs: f"Phản hồi AI cho: {user_message}",
    )
    monkeypatch.setattr(
        "app.services.campaign_jobs.send_page_message",
        lambda recipient_id, message, access_token: {"recipient_id": recipient_id, "message_id": "m_out_1"},
    )

    processed = process_task_queue("worker-test@local")
    assert processed == 1

    db_session.expire_all()
    saved_log = db_session.query(InboxMessageLog).filter(InboxMessageLog.id == log.id).first()
    assert saved_log.status == InteractionStatus.replied
    assert saved_log.ai_reply == "Phản hồi AI cho: Cho mình xin giá"
    assert saved_log.facebook_reply_message_id == "m_out_1"
