from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, func,
    BigInteger
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    project_id = Column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    uploaded_by = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    original_name = Column(String(255), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    mime_type = Column(String(120), nullable=True)
    ext = Column(String(16), nullable=True)

    project_type = Column(String(50), nullable=True, index=True)

    size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(128), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )

    project = relationship("Project", back_populates="files")