from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import hashlib

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def is_bcrypt_hash(s: str) -> bool:
    return isinstance(s, str) and (
        s.startswith(("$2a$", "$2b$", "$2y$")) or s.startswith("$bcrypt-sha256$")
    )

def is_sha256_hex(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

def verify_and_upgrade(plain_password: str, stored_hash: str, upgrade_cb) -> bool:
    try:
        return verify_password(plain_password, stored_hash)
    except UnknownHashError:
        pass
    if is_sha256_hex(stored_hash):
        digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        if digest == stored_hash:
            new_hash = hash_password(plain_password)
            try:
                upgrade_cb(new_hash)
            except Exception:
                pass
            return True
    return False

def create_user(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    password: Optional[str] = None,
    password_hash: Optional[str] = None,
    avatar_url: Optional[str] = None,
    locale: str = "en",
    time_zone: str = "UTC",
    role_id: int = 1,
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    raw_password = password or password_hash
    if not raw_password:
        raise HTTPException(status_code=422, detail="Password is required")
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hash_password(raw_password),
        avatar_url=avatar_url,
        locale=locale,
        time_zone=time_zone,
        role_id=role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    def _upgrade(new_hash: str):
        user.password_hash = new_hash
        db.add(user)
        db.commit()
    if not verify_and_upgrade(password, user.password_hash, _upgrade):
        try:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            db.add(user)
            db.commit()
        except Exception:
            pass
        return None
    try:
        user.failed_login_count = 0
        user.last_login_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        pass
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def issue_token(user: User):
    payload = {"sub": str(user.id), "email": user.email}
    if getattr(user, "role_id", None) is not None:
        payload["role_id"] = int(user.role_id)
    return create_access_token(payload)

def list_users(db: Session):
    return db.query(User).all()

def get_user(db: Session, user_id: int):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
