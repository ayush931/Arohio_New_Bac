from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.controllers import user_controller

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


# --------- helpers ---------
def _serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "email": u.email,
        "avatar_url": u.avatar_url,
        "locale": u.locale,
        "time_zone": u.time_zone,
        "is_active": u.deleted_at is None,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "failed_login_count": u.failed_login_count,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
        "role_id": getattr(u, "role_id", None),
        "phone_number": getattr(u, "phone_number", None),
        "job_title": getattr(u, "job_title", None),
        "company_id": getattr(u, "company_id", None),
    }


def _paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total}


# --------- schemas ---------
class AdminUserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role_id: Optional[int] = None
    is_active: bool = True
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    company_id: Optional[int] = None
    locale: str = "en"
    time_zone: str = "UTC"
    avatar_url: Optional[str] = None


class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    company_id: Optional[int] = None
    locale: Optional[str] = None
    time_zone: Optional[str] = None
    avatar_url: Optional[str] = None


# --------- routes ---------

@router.get("/")
def admin_list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    q: Optional[str] = Query(None),
    include_inactive: bool = Query(True),
    include_deleted: bool = Query(False),
    role_id: Optional[int] = Query(None),
):
    qs = db.query(User)
    if not include_deleted:
        qs = qs.filter(User.deleted_at.is_(None))
    if not include_inactive:
        qs = qs.filter(User.is_active.is_(True))
    if role_id is not None and hasattr(User, "role_id"):
        qs = qs.filter(User.role_id == role_id)
    if q:
        like = f"%{q}%"
        parts = [User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like)]
        if hasattr(User, "phone_number"):
            parts.append(User.phone_number.ilike(like))
        if hasattr(User, "job_title"):
            parts.append(User.job_title.ilike(like))
        qs = qs.filter(or_(*parts))
    data = _paginate(qs.order_by(User.id.desc()), page, page_size)
    return {
        "items": [_serialize_user(u) for u in data["items"]],
        "total": data["total"],
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}")
def admin_get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u or u.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(u)


@router.post("/", status_code=status.HTTP_201_CREATED)
def admin_create_user(payload: AdminUserCreate = Body(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    if hasattr(user_controller, "hash_password"):
        password_hash = user_controller.hash_password(payload.password)
    else:
        from passlib.hash import bcrypt
        password_hash = bcrypt.hash(payload.password)

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=password_hash,
        avatar_url=payload.avatar_url,
        locale=payload.locale,
        time_zone=payload.time_zone,
        is_active=payload.is_active,
    )
    if hasattr(User, "role_id"):
        user.role_id = payload.role_id
    if hasattr(User, "phone_number"):
        user.phone_number = payload.phone_number
    if hasattr(User, "job_title"):
        user.job_title = payload.job_title
    if hasattr(User, "company_id"):
        user.company_id = payload.company_id

    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.patch("/{user_id}")
def admin_update_user(user_id: int, payload: AdminUserUpdate = Body(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email and payload.email != u.email:
        dup = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None), User.id != user_id).first()
        if dup:
            raise HTTPException(status_code=400, detail="Email already exists")
        u.email = payload.email

    if payload.first_name is not None:
        u.first_name = payload.first_name
    if payload.last_name is not None:
        u.last_name = payload.last_name
    if payload.role_id is not None and hasattr(User, "role_id"):
        u.role_id = payload.role_id
    if payload.is_active is not None:
        u.is_active = payload.is_active
    if payload.phone_number is not None and hasattr(User, "phone_number"):
        u.phone_number = payload.phone_number
    if payload.job_title is not None and hasattr(User, "job_title"):
        u.job_title = payload.job_title
    if payload.company_id is not None and hasattr(User, "company_id"):
        u.company_id = payload.company_id
    if payload.locale is not None:
        u.locale = payload.locale
    if payload.time_zone is not None:
        u.time_zone = payload.time_zone
    if payload.avatar_url is not None:
        u.avatar_url = payload.avatar_url

    if payload.password:
        if hasattr(user_controller, "hash_password"):
            u.password_hash = user_controller.hash_password(payload.password)
        else:
            from passlib.hash import bcrypt
            u.password_hash = bcrypt.hash(payload.password)

    db.commit()
    db.refresh(u)
    return _serialize_user(u)


@router.post("/{user_id}/toggle")
def admin_toggle_active(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = not bool(u.is_active)
    db.commit()
    db.refresh(u)
    return _serialize_user(u)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    hard: bool = Query(False, description="Set true to permanently delete"),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u or (u.deleted_at is not None and not hard):
        # already gone (soft) or not found
        raise HTTPException(status_code=404, detail="User not found")

    if hard:
        db.delete(u)
    else:
        u.deleted_at = datetime.utcnow()
    db.commit()
    return
