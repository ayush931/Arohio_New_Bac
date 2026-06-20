from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# Base shared fields
class ContactSupportBase(BaseModel):
    user_id: Optional[int] = None            # FK to users.id
    assigned_to: Optional[int] = None        # FK to users.id
    name: str = Field(..., max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=30)
    subject: str = Field(..., max_length=200)
    message: str
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = "new"            # new / in_progress / resolved / closed
    priority: Optional[str] = "normal"       # low / normal / high / urgent
    is_resolved: Optional[bool] = False
    resolution_notes: Optional[str] = None

# For creating a new ticket
class ContactSupportCreate(ContactSupportBase):
    # ensure these are required
    name: str
    email: EmailStr
    subject: str
    message: str

# For partial updates (PATCH)
class ContactSupportUpdate(BaseModel):
    user_id: Optional[int] = None
    assigned_to: Optional[int] = None
    name: Optional[str] = Field(None, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    subject: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    priority: Optional[str] = None
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None

# For returning a ticket (read)
class ContactSupportOut(ContactSupportBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # (pydantic v2) or orm_mode = True (pydantic v1)
