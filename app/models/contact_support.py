from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, func, BigInteger
)
from datetime import datetime
from app.db.database import Base

class ContactSupport(Base):
    __tablename__ = "contact_support"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # match users.id (BIGINT)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    assigned_to = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)

    status = Column(String(50), default="new", nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                        server_default=func.now(), nullable=False)
