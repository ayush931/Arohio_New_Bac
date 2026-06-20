# app/api/v1/routes_contact_support.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db  # your SessionLocal dependency
from app.models.contact_support import ContactSupport
from app.schemas.contact_support import (
    ContactSupportCreate, ContactSupportUpdate, ContactSupportOut
)

router = APIRouter(prefix="/contact-support", tags=["Contact Support"])

# ---------- Helpers ----------
def _get_or_404(db: Session, ticket_id: int) -> ContactSupport:
    obj = db.query(ContactSupport).filter(ContactSupport.id == ticket_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contact support ticket not found")
    return obj

# ---------- Create ----------
@router.post("/", response_model=ContactSupportOut, status_code=status.HTTP_201_CREATED)
def create_contact_support(payload: ContactSupportCreate, db: Session = Depends(get_db)):
    obj = ContactSupport(**payload.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# ---------- List with filters & pagination ----------
@router.get("/", response_model=List[ContactSupportOut])
def list_contact_support(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None, description="free text search on name/email/subject/message"),
    status_: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    user_id: Optional[int] = None,
    assigned_to: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    order_by: Optional[str] = Query("created_at", regex="^(created_at|updated_at|priority|status)$"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
):
    query = db.query(ContactSupport)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                ContactSupport.name.ilike(like),
                ContactSupport.email.ilike(like),
                ContactSupport.subject.ilike(like),
                ContactSupport.message.ilike(like),
            )
        )
    if status_:
        query = query.filter(ContactSupport.status == status_)
    if priority:
        query = query.filter(ContactSupport.priority == priority)
    if user_id is not None:
        query = query.filter(ContactSupport.user_id == user_id)
    if assigned_to is not None:
        query = query.filter(ContactSupport.assigned_to == assigned_to)
    if is_resolved is not None:
        query = query.filter(ContactSupport.is_resolved == is_resolved)

    # ordering
    order_col = getattr(ContactSupport, order_by)
    query = query.order_by(desc(order_col) if order == "desc" else order_col)

    # pagination
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items

# (Optional) total count endpoint for UI pagination
@router.get("/count", summary="Total items count (after filters)")
def count_contact_support(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    status_: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    user_id: Optional[int] = None,
    assigned_to: Optional[int] = None,
    is_resolved: Optional[bool] = None,
):
    query = db.query(func.count(ContactSupport.id))

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                ContactSupport.name.ilike(like),
                ContactSupport.email.ilike(like),
                ContactSupport.subject.ilike(like),
                ContactSupport.message.ilike(like),
            )
        )
    if status_:
        query = query.filter(ContactSupport.status == status_)
    if priority:
        query = query.filter(ContactSupport.priority == priority)
    if user_id is not None:
        query = query.filter(ContactSupport.user_id == user_id)
    if assigned_to is not None:
        query = query.filter(ContactSupport.assigned_to == assigned_to)
    if is_resolved is not None:
        query = query.filter(ContactSupport.is_resolved == is_resolved)

    total = query.scalar() or 0
    return {"total": total}

# ---------- Read one ----------
@router.get("/{ticket_id}", response_model=ContactSupportOut)
def get_contact_support(ticket_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, ticket_id)

# ---------- Update (partial) ----------
@router.patch("/{ticket_id}", response_model=ContactSupportOut)
def update_contact_support(ticket_id: int, payload: ContactSupportUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ticket_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# ---------- Replace (full PUT) ----------
@router.put("/{ticket_id}", response_model=ContactSupportOut)
def replace_contact_support(ticket_id: int, payload: ContactSupportCreate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ticket_id)
    data = payload.model_dump(exclude_unset=False)
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# ---------- Delete (hard delete) ----------
@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_support(ticket_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ticket_id)
    db.delete(obj)
    db.commit()
    return None
