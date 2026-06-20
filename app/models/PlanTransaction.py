from sqlalchemy import (
    Column, String, DateTime, ForeignKey, func,
    BigInteger, Numeric, Index
)
from datetime import datetime
from app.db.database import Base


class PlanTransaction(Base):
    __tablename__ = "plan_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    user_plan_id = Column(BigInteger, ForeignKey("user_plans.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False)

    payment_mode = Column(String(50), nullable=False)   
    status = Column(String(50), nullable=False)         

    transaction_ref = Column(String(255), nullable=True)

    paid_at = Column(DateTime, nullable=True)

    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow,
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow,
                        server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_plan_transactions_user", "user_id"),
    )