from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import Campaign, Video, CampaignStatus
from app.services.ytdlp_crawler import extract_metadata, download_video

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

class CampaignCreate(BaseModel):
    name: str
    source_url: str
    auto_post: bool = False
    target_page_id: str | None = None
    schedule_interval: int = 0

@router.post("/")
def create_campaign(campaign_in: CampaignCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_campaign = Campaign(
        name=campaign_in.name,
        source_url=campaign_in.source_url,
        auto_post=campaign_in.auto_post,
        target_page_id=campaign_in.target_page_id,
        schedule_interval=campaign_in.schedule_interval,
        status=CampaignStatus.active
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    
    background_tasks.add_task(process_campaign_worker, str(db_campaign.id), campaign_in.source_url, db)
    return {"message": "Campaign created and processing started", "campaign": db_campaign.id}

@router.get("/")
def get_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()

@router.get("/stats")
def get_video_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(Video).count()
    pending = db.query(Video).filter(Video.status == 'pending').count()
    ready = db.query(Video).filter(Video.status == 'ready').count()
    posted = db.query(Video).filter(Video.status == 'posted').count()
    failed = db.query(Video).filter(Video.status == 'failed').count()
    
    # Tính toán thời gian hàng chờ
    next_publish = db.query(func.min(Video.publish_time)).filter(Video.status == 'ready').scalar()
    last_publish = db.query(func.max(Video.publish_time)).filter(Video.status == 'ready').scalar()
    
    return {
        "total": total,
        "pending": pending,
        "ready": ready,
        "posted": posted,
        "failed": failed,
        "next_publish": next_publish.isoformat() if next_publish else None,
        "last_publish": last_publish.isoformat() if last_publish else None
    }

@router.get("/videos")
def get_videos(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    total = db.query(Video).count()
    videos = db.query(Video).order_by(Video.publish_time.desc(), Video.id.desc()).offset(offset).limit(limit).all()
    
    return {
        "videos": videos,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

def process_campaign_worker(campaign_id: str, source_url: str, db: Session):
    try:
        info = extract_metadata(source_url)
        entries = info.get('entries', [info]) if 'entries' in info else [info]
        
        # Đảo ngược danh sách để video CŨ NHẤT (ở cuối) được xếp lịch ĐĂNG TRƯỚC
        entries = list(reversed(entries))
        
        campaign = db.query(Campaign).filter(Campaign.id == uuid.UUID(campaign_id)).first()
        target_page_id = campaign.target_page_id if campaign else None
        schedule_interval = campaign.schedule_interval if campaign else 0
        
        # LOGIC MỚI: Tính toán thời điểm bắt đầu nối đuôi hàng chờ
        now = datetime.utcnow()
        start_time = now
        
        if target_page_id and schedule_interval > 0:
            from sqlalchemy import func
            # Tìm thời gian publish của video cuối cùng thuộc cùng Fanpage này
            last_publish = db.query(func.max(Video.publish_time)).join(Campaign).filter(
                Campaign.target_page_id == target_page_id
            ).scalar()
            
            if last_publish and last_publish > now:
                # Nếu còn hàng chờ trong tương lai, nối tiếp vào sau 1 khoảng interval
                start_time = last_publish + timedelta(minutes=schedule_interval)
                print(f"DEBUG SCHEDULER: Nối đuôi vào hàng chờ sau {last_publish}. Bắt đầu từ {start_time}")
            else:
                print(f"DEBUG SCHEDULER: Hàng chờ trống hoặc đã qua. Bắt đầu từ {start_time}")
        
        added_count = 0
        for entry in entries:
            video_url = entry.get('webpage_url', entry.get('url'))
            if not video_url: continue
            
            # Check if video already exists
            existing_vid = db.query(Video).filter(Video.original_id == entry.get('id')).first()
            if existing_vid: continue
            
            publish_time = start_time + timedelta(minutes=added_count * schedule_interval)
            
            title = entry.get('title', '').strip()
            description = entry.get('description', '').strip()
            
            # TikTok: description là caption đầy đủ nhất.
            original_caption = description if description else title
            print(f"DEBUG CRAWL: ID={entry.get('id')} | Final={original_caption[:50]}...", flush=True)

            db_video = Video(
                campaign_id=uuid.UUID(campaign_id),
                original_id=entry.get('id', str(uuid.uuid4())),
                original_caption=original_caption,
                status="pending",
                publish_time=publish_time
            )
            db.add(db_video)
            db.commit()
            db.refresh(db_video)
            added_count += 1
            
            out_path, vid_id = download_video(video_url, "tiktok")
            if out_path:
                db_video.file_path = out_path
                db_video.status = "ready"
                db.commit()
    except Exception as e:
        print(f"Worker Error: {e}")
