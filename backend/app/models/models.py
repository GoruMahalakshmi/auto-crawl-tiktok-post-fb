import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class CampaignStatus(str, enum.Enum):
    active = "active"
    paused = "paused"

class VideoStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    ready = "ready"
    posted = "posted"
    failed = "failed"

class InteractionStatus(str, enum.Enum):
    pending = "pending"
    replied = "replied"
    failed = "failed"

class TaskStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    source_url = Column(String)  # TikTok URL
    status = Column(Enum(CampaignStatus), default=CampaignStatus.active)
    auto_post = Column(Boolean, default=False)
    target_page_id = Column(String, nullable=True)
    schedule_interval = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    videos = relationship("Video", back_populates="campaign")

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    original_id = Column(String, unique=True, index=True)
    file_path = Column(String, nullable=True)
    original_caption = Column(String, nullable=True)
    ai_caption = Column(String, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.pending)
    publish_time = Column(DateTime, nullable=True)
    fb_post_id = Column(String, nullable=True)

    campaign = relationship("Campaign", back_populates="videos")

class FacebookPage(Base):
    __tablename__ = "facebook_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, unique=True, index=True)
    page_name = Column(String)
    long_lived_access_token = Column(String)

class InteractionLog(Base):
    __tablename__ = "interactions_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, ForeignKey("facebook_pages.page_id"))
    post_id = Column(String)
    comment_id = Column(String, unique=True)
    user_id = Column(String)
    user_message = Column(String)
    ai_reply = Column(String, nullable=True)
    status = Column(Enum(InteractionStatus), default=InteractionStatus.pending)

class TaskQueue(Base):
    __tablename__ = "task_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String, index=True)
    payload = Column(JSONB)
    status = Column(Enum(TaskStatus), default=TaskStatus.queued)
    attempts = Column(Integer, default=0)
    locked_at = Column(DateTime, nullable=True)
