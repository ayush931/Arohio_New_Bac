from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, BigInteger, Index
)
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        # handy composite indexes for unread lists & activity feeds
        Index("ix_audits_is_read_created_at", "is_read", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    # PK matches users.id type (BIGINT)
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    action = Column(String(128), nullable=False, index=True)

    # FKs MUST match users.id type exactly (BIGINT here)
    actor_user_id  = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    target_user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    actor_message  = Column(Text, nullable=True)
    custom_message = Column(Text, nullable=True)

    is_read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    meta = Column(MySQLJSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # relationships (no cascade deletes—FKs are SET NULL)
    actor  = relationship("User", foreign_keys=[actor_user_id])
    target = relationship("User", foreign_keys=[target_user_id])

    def __repr__(self) -> str:
        return f"<Audit id={self.id} action={self.action} actor={self.actor_user_id} target={self.target_user_id}>"
