from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)

    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    phone_number = Column(String(20), nullable=True)
    job_title = Column(String(100), nullable=True)

    avatar_url = Column(String(255), nullable=True)
    locale = Column(String(10), default="en")
    time_zone = Column(String(50), default="UTC")

    role_id = Column(Integer, default=1)

    failed_login_count = Column(Integer, default=0)
    last_login_at = Column(DateTime, nullable=True)

    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)