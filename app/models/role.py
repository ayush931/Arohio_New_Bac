from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, func, event
from app.db.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # "user", "admin"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

# Seed default roles when table is first created
@event.listens_for(Role.__table__, "after_create")
def seed_roles(target, connection, **kw):
    connection.execute(
        Role.__table__.insert(),
        [
            {"name": "user", "description": "Default application user", "is_active": True},
            {"name": "admin", "description": "Administrator role", "is_active": True},
        ],
    )
