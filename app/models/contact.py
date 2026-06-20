# app/models/contact.py
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, func
)
from datetime import datetime
from app.db.database import Base

class ContactTicket(Base):
    """
    Merged Contact + Support Ticket model.
    Tracks who submitted the ticket (user_id) plus admin fields.
    """
    __tablename__ = "contact"

    # ---- Public fields (from the form) ----
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # If logged-in user submits, link to users.id. Null = guest
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # e.g. Billing, Technical, Feedback

    # ---- Admin / internal tracking fields ----
    status = Column(String(50), default="new", nullable=False)      # new / in_progress / resolved / closed
    priority = Column(String(20), default="normal", nullable=False) # low / normal / high / urgent
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # staff assigned
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)

    # ---- Timestamps ----
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<ContactTicket {self.id} subj='{self.subject}' user_id={self.user_id}>"
