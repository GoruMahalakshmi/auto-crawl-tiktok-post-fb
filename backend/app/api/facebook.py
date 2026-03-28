from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import FacebookPage

router = APIRouter(prefix="/facebook", tags=["Facebook"])

class FacebookPageCreate(BaseModel):
    page_id: str
    page_name: str
    long_lived_access_token: str

@router.post("/config")
def set_facebook_config(page_in: FacebookPageCreate, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_in.page_id).first()
    if page:
        page.page_name = page_in.page_name
        page.long_lived_access_token = page_in.long_lived_access_token
    else:
        page = FacebookPage(
            page_id=page_in.page_id,
            page_name=page_in.page_name,
            long_lived_access_token=page_in.long_lived_access_token
        )
        db.add(page)
    db.commit()
    return {"message": "Đã lưu cấu hình Facebook Token thành công!"}

@router.get("/config")
def get_facebook_config(db: Session = Depends(get_db)):
    pages = db.query(FacebookPage).all()
    if pages:
        return [{"page_id": p.page_id, "page_name": p.page_name, "has_token": bool(p.long_lived_access_token)} for p in pages]
    return []
