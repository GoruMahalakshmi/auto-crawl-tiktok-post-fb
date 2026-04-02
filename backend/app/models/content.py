import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now
from app.models.common import JSON_TYPE


class CampaignStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class VideoStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    ready = "ready"
    posted = "posted"
    failed = "failed"


class AffiliateCommentStatus(str, enum.Enum):
    disabled = "disabled"
    queued = "queued"
    posted = "posted"
    operator_required = "operator_required"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    source_url = Column(String)
    source_platform = Column(String, nullable=True, index=True)
    source_kind = Column(String, nullable=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.active)
    auto_post = Column(Boolean, default=False)
    target_page_id = Column(String, nullable=True)
    schedule_interval = Column(Integer, default=0)
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, default="idle")
    last_sync_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    videos = relationship("Video", back_populates="campaign")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("campaign_id", "original_id", name="uq_videos_campaign_original"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(Uuid(as_uuid=True), ForeignKey("campaigns.id"))
    original_id = Column(String, index=True)
    source_platform = Column(String, nullable=True, index=True)
    source_kind = Column(String, nullable=True)
    source_video_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    original_caption = Column(String, nullable=True)
    ai_caption = Column(String, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.pending)
    publish_time = Column(DateTime, nullable=True)
    fb_video_id = Column(String, nullable=True)
    fb_post_id = Column(String, nullable=True)
    fb_permalink_url = Column(String, nullable=True)
    affiliate_comment_status = Column(Enum(AffiliateCommentStatus), default=AffiliateCommentStatus.disabled, nullable=False)
    affiliate_comment_text = Column(String, nullable=True)
    affiliate_comment_fb_id = Column(String, nullable=True)
    affiliate_comment_fb_ids = Column(JSON_TYPE, nullable=True)
    affiliate_comment_error = Column(String, nullable=True)
    affiliate_comment_attempts = Column(Integer, default=0, nullable=False)
    affiliate_comment_target_count = Column(Integer, default=0, nullable=False)
    affiliate_comment_completed_count = Column(Integer, default=0, nullable=False)
    affiliate_comment_requested_at = Column(DateTime, nullable=True)
    affiliate_commented_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    campaign = relationship("Campaign", back_populates="videos")
