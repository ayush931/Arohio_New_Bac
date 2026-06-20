from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, func,
    BigInteger, Integer, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)   
    description = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    file_count_cached = Column(Integer, default=0, nullable=False)
    last_file_at_cached = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow,
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                        server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_project_owner_name"),
        Index("ix_projects_updated_at", "updated_at"),
    )

    files = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
