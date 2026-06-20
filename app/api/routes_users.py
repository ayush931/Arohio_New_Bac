from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os, shutil, logging

from app.core.database import get_db
from app.controllers import user_controller
from app.models.user import User
from datetime import datetime, timedelta
from app.models.UserPlan import UserPlan

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)

# ---------- Existing payloads ----------
class UserCreateBody(BaseModel):
    first_name: str
    last_name: str
    email: str
    password_hash: str
    avatar_url: str | None = None
    locale: str = "en"
    time_zone: str = "UTC"


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/", status_code=201)
def create_user(payload: UserCreateBody, db: Session = Depends(get_db)):
    logger.info("POST /users create_user email=%s", payload.email)

    user = user_controller.create_user(
        db=db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=payload.password_hash,
        avatar_url=payload.avatar_url,
        locale=payload.locale,
        time_zone=payload.time_zone,
    )

    now = datetime.utcnow()

    plan = UserPlan(
        user_id=user.id,
        plan_name="Free Plan",
        pdf_limit=10,
        image_limit=50,
        pdf_used=0,
        image_used=0,
        start_date=now,
        end_date=now + timedelta(days=30),
        is_active=True,
        assigned_by=None,
        created_at=now,
        updated_at=now
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return user


@router.post("/login")
def login(payload: LoginBody, db: Session = Depends(get_db)):
    logger.info("POST /users/login email=%s", payload.email)
    user = user_controller.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    if not user:
        logger.warning("Login failed for %s", payload.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = user_controller.issue_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role_id": getattr(user, "role_id", None),
            "role": getattr(getattr(user, "role", None), "name", None),
        },
    }


@router.get("/")
def get_users(db: Session = Depends(get_db)):
    logger.info("GET /users")
    return user_controller.list_users(db)


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    logger.info("GET /users/%s", user_id)
    return user_controller.get_user(db, user_id)

# =========================
#       PROFILE APIs
# =========================

@router.get("/{user_id}/profile")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    logger.info("GET /users/%s/profile", user_id)
    user: User | None = (
        db.query(User).filter(User.id == user_id, User.deleted_at == None).first()
    )
    if not user:
        logger.warning("User %s not found (profile)", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return {
        "name": name,
        "email": user.email,
        "jobTitle": getattr(user, "job_title", "") or "",
        "phone": getattr(user, "phone_number", "") or "",
        "avatar_url": user.avatar_url or "",
        "role_id": getattr(user, "role_id", None),
    }


UPLOAD_DIR = os.path.join("public", "profile_images")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{user_id}/profile")
def update_profile(
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
    jobTitle: str = Form(""),
    phone: str = Form(""),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    logger.info("POST /users/%s/profile", user_id)
    user: User | None = (
        db.query(User).filter(User.id == user_id, User.deleted_at == None).first()
    )
    if not user:
        logger.warning("User %s not found (update)", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    # split name into first/last
    parts = name.split(" ", 1)
    user.first_name = parts[0]
    user.last_name = parts[1] if len(parts) > 1 else ""
    user.email = email
    if hasattr(user, "job_title"):
        user.job_title = jobTitle
    if hasattr(user, "phone_number"):
        user.phone_number = phone

    # avatar upload
    if avatar:
        if not avatar.content_type or not avatar.content_type.lower().startswith("image/"):
            raise HTTPException(status_code=400, detail="Avatar must be an image")
        safe_name = avatar.filename.replace(" ", "_")
        filename = f"{user_id}_{safe_name}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
        user.avatar_url = f"/profile_images/{filename}"

    db.commit()
    db.refresh(user)
    return {"status": "ok", "avatar_url": user.avatar_url or ""}


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    user_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    logger.info("POST /users/%s/password", user_id)
    user: User | None = (
        db.query(User).filter(User.id == user_id, User.deleted_at == None).first()
    )
    if not user:
        logger.warning("User %s not found (password)", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    # verify password
    if hasattr(user_controller, "verify_password"):
        verify_ok = user_controller.verify_password(current_password, user.password_hash)
    else:
        from passlib.hash import bcrypt
        verify_ok = bcrypt.verify(current_password, user.password_hash)

    if not verify_ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # hash new password
    if hasattr(user_controller, "hash_password"):
        user.password_hash = user_controller.hash_password(new_password)
    else:
        from passlib.hash import bcrypt
        user.password_hash = bcrypt.hash(new_password)

    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
