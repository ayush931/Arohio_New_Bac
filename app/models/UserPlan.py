from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, func,
    BigInteger, Integer, Index
)
from datetime import datetime
from app.db.database import Base


class UserPlan(Base):
    __tablename__ = "user_plans"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    plan_name = Column(String(255), nullable=True)

    pdf_limit = Column(Integer, nullable=False)
    image_limit = Column(Integer, nullable=False)

    pdf_used = Column(Integer, default=0, nullable=False)
    image_used = Column(Integer, default=0, nullable=False)

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    assigned_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow,
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow,
                        server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_user_plans_user_active", "user_id", "is_active"),
    )