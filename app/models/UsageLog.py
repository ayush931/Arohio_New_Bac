from sqlalchemy import (
    Column, String, DateTime, ForeignKey, func,
    BigInteger, Integer, Index
)
from datetime import datetime
from app.db.database import Base
from sqlalchemy.orm import relationship


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    user_plan_id = Column(BigInteger, ForeignKey("user_plans.id", ondelete="CASCADE"), nullable=False)

    type = Column(String(50), nullable=False)  

    file_name = Column(String(255), nullable=True)

    credits_used = Column(Integer, default=1, nullable=False)

    reference_id = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow,
                        server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_usage_logs_user", "user_id"),
    )

