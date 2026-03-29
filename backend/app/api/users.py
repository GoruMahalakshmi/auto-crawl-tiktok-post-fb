from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.api.auth import require_admin, require_authenticated_user
from app.core.database import get_db
from app.models.models import User, UserRole
from app.services.accounts import count_admin_users, create_user, generate_temporary_password, serialize_user
from app.services.observability import record_event
from app.services.security import hash_password

router = APIRouter(prefix="/users", tags=["Người dùng"])


def parse_uuid_or_400(raw_id: str):
    try:
        return uuid.UUID(raw_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Mã người dùng không hợp lệ.") from exc


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    display_name: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=8, max_length=100)
    role: str = Field(default=UserRole.operator.value)


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    role: str | None = None
    is_active: bool | None = None


@router.get("/")
def get_users(
    _: User = Depends(require_authenticated_user),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.role.asc(), User.created_at.asc()).all()
    return {"users": [serialize_user(user) for user in users], "viewer": serialize_user(admin_user)}


@router.post("/")
def create_user_endpoint(
    payload: UserCreateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        user = create_user(
            db,
            username=payload.username,
            password=payload.password,
            role=payload.role,
            display_name=payload.display_name,
            must_change_password=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_event(
        "auth",
        "info",
        "Đã tạo người dùng mới.",
        db=db,
        actor_user_id=str(admin_user.id),
        details={"username": user.username, "role": user.role.value},
    )
    return {"message": f"Đã tạo người dùng '{user.username}'.", "user": serialize_user(user)}


@router.patch("/{user_id}")
def update_user_endpoint(
    user_id: str,
    payload: UserUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == parse_uuid_or_400(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if payload.role:
        try:
            new_role = UserRole(payload.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Vai trò người dùng không hợp lệ.") from exc
        if user.role == UserRole.admin and new_role != UserRole.admin and count_admin_users(db, active_only=True, exclude_user_id=str(user.id)) == 0:
            raise HTTPException(status_code=400, detail="Hệ thống phải luôn còn ít nhất một quản trị viên đang hoạt động.")
        user.role = new_role

    if payload.is_active is not None:
        if user.role == UserRole.admin and not payload.is_active and count_admin_users(db, active_only=True, exclude_user_id=str(user.id)) == 0:
            raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa quản trị viên cuối cùng.")
        user.is_active = payload.is_active

    if payload.display_name is not None:
        user.display_name = payload.display_name.strip() or None

    db.commit()
    db.refresh(user)
    record_event(
        "auth",
        "info",
        "Đã cập nhật thông tin người dùng.",
        db=db,
        actor_user_id=str(admin_user.id),
        details={"target_user": user.username},
    )
    return {"message": f"Đã cập nhật người dùng '{user.username}'.", "user": serialize_user(user)}


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == parse_uuid_or_400(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    temporary_password = generate_temporary_password()
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    db.commit()
    db.refresh(user)

    record_event(
        "auth",
        "warning",
        "Đã đặt lại mật khẩu người dùng.",
        db=db,
        actor_user_id=str(admin_user.id),
        details={"target_user": user.username},
    )
    return {
        "message": f"Đã đặt lại mật khẩu cho '{user.username}'.",
        "temporary_password": temporary_password,
        "user": serialize_user(user),
    }


@router.delete("/{user_id}")
def delete_user_endpoint(
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == parse_uuid_or_400(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if str(user.id) == str(admin_user.id):
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản đang đăng nhập.")

    if user.role == UserRole.admin and count_admin_users(db, active_only=True, exclude_user_id=str(user.id)) == 0:
        raise HTTPException(status_code=400, detail="Không thể xóa quản trị viên cuối cùng đang hoạt động.")

    deleted_username = user.username
    deleted_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    db.delete(user)
    db.commit()

    record_event(
        "auth",
        "warning",
        "Đã xóa vĩnh viễn người dùng.",
        db=db,
        actor_user_id=str(admin_user.id),
        details={"target_user": deleted_username, "role": deleted_role},
    )
    return {"message": f"Đã xóa người dùng '{deleted_username}' khỏi hệ thống."}
