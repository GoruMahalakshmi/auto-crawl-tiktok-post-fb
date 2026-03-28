from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Video, Campaign, FacebookPage
from app.services.ai_generator import generate_caption
from app.services.fb_graph import upload_video_to_facebook
import traceback
import os
from datetime import datetime

scheduler = BackgroundScheduler()

# def ai_caption_job():
#     print("CRON: Đang quét video thiếu AI Caption...")
#     db: Session = SessionLocal()
#     try:
#         # Lấy các video chưa có AI caption và chưa đăng
#         videos = db.query(Video).filter(
#             Video.ai_caption == None,
#             Video.status != 'posted'
#         ).limit(5).all() # Xử lý mỗi lần 5 video để tránh rate limit
#         
#         for vid in videos:
#             print(f"CRON: Đang sinh AI Caption cho video {vid.original_id}...", flush=True)
#             try:
#                 vid.ai_caption = generate_caption(vid.original_caption)
#                 db.commit()
#                 print(f"CRON: Đã sinh xong AI Caption cho {vid.original_id}", flush=True)
#             except Exception as e:
#                 print(f"CRON Error sinh caption cho {vid.original_id}: {e}")
#                 
#     except Exception as e:
#         print(f"CRON AI Job Error: {e}")
#     finally:
#         db.close()

def auto_post_job():
    print("CRON: Đang quét video sẵn sàng upload (Throttling: 1 video/page/minute)...")
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        # Lấy danh sách tất cả các Fanpage để xử lý riêng biệt
        pages = db.query(FacebookPage).all()
        
        for page in pages:
            # Với mỗi Fanpage, chỉ lấy DUY NHẤT 1 video cũ nhất đang chờ
            vid = db.query(Video).join(Campaign).filter(
                Campaign.target_page_id == page.page_id,
                Video.status == 'ready',
                Video.publish_time <= now
            ).order_by(Video.publish_time.asc()).first()
            
            if not vid:
                continue
                
            print(f"CRON: [Page {page.page_name}] Đang xử lý video {vid.original_id}...")
            
            if vid.campaign.auto_post:
                # [Optimization] Chỉ sinh AI caption vào đúng thời điểm đăng bài (Just-In-Time)
                if not vid.ai_caption:
                    print(f"CRON: [Just-In-Time] Đang sinh AI Caption qua Gemini cho Page {page.page_name}...")
                    vid.ai_caption = generate_caption(vid.original_caption)
                    db.commit() # Lưu vào DB ngay lập tức
                    print(f"CRON: [SUCCESS] Đã sinh Caption AI.")

                # Upload Facebook
                print(f"CRON: Uploading video {vid.original_id} tới Facebook...")
                res = upload_video_to_facebook(
                    file_path=vid.file_path,
                    caption=vid.ai_caption,
                    page_id=page.page_id,
                    access_token=page.long_lived_access_token
                )
                
                if 'id' in res:
                    vid.fb_post_id = res['id']
                    vid.status = 'posted'
                    print(f"CRON: [SUCCESS] Page {page.page_name} -> Post ID: {vid.fb_post_id}")
                    
                    # Xóa file local sau khi upload
                    if vid.file_path and os.path.exists(vid.file_path):
                        try:
                            # Tách logic xóa file sang log riêng
                            os.remove(vid.file_path)
                            print(f"CRON: Đã xóa file local: {vid.file_path}")
                        except Exception as e:
                            print(f"CRON: Lỗi khi xóa file: {e}")
                else:
                    vid.status = 'failed'
                    vid.fb_post_id = str(res.get('error', res))
                    print(f"CRON: [FAILED] Page {page.page_name} -> Error: {res}")
                
                db.commit()
    except Exception as e:
        print(f"CRON Lỗi: {e}")
        traceback.print_exc()
    finally:
        db.close()

def start_scheduler():
    # Gỡ bỏ ai_caption_job để tiết kiệm API Limit của Gemini
    # scheduler.add_job(ai_caption_job, 'interval', seconds=30)
    scheduler.add_job(auto_post_job, 'interval', minutes=1)
    scheduler.start()
