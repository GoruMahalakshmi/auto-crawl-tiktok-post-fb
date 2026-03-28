from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()

def get_expected_token():
    return f"social_token_{settings.ADMIN_PASSWORD}"

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
def login(creds: LoginRequest):
    if creds.password == settings.ADMIN_PASSWORD:
        return {"access_token": get_expected_token(), "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Sai mật khẩu truy cập!")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != get_expected_token():
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập hết hạn hoặc Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
