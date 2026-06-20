from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field

# what the client sends when submitting a contact form
class ContactCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2)

# allowed status updates
AllowedStatus = Literal["new", "read", "replied", "archived"]

class ContactUpdate(BaseModel):
    status: AllowedStatus

# what we return to clients
class ContactOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: str
    message: str
    status: AllowedStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # (Pydantic v2) replaces orm_mode=True
