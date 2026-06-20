# app/models/newsletter.py
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Enum, DateTime
from app.db.database import Base
import enum

class NewsletterStatus(str, enum.Enum):
    subscribed = "subscribed"
    unsubscribed = "unsubscribed"
    bounced = "bounced"
    pending = "pending"

class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(150))
    status = Column(Enum(NewsletterStatus), default=NewsletterStatus.subscribed, nullable=False)
    token = Column(String(64))
    subscribed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unsubscribed_at = Column(DateTime)
    ip_address = Column(String(45))
    source = Column(String(100))
