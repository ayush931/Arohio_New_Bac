from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.role import Role

router = APIRouter(prefix="/roles", tags=["roles"])

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str):
        v = (v or "").strip()
        if not v:
            raise ValueError("name is required")
        return v

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class PaginatedRoles(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[RoleOut]

def _get_role_or_404(db: Session, role_id: int) -> Role:
    role = (
        db.query(Role)
        .filter(Role.id == role_id, Role.deleted_at.is_(None))
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

def _assert_unique_name(db: Session, name: str, exclude_id: Optional[int] = None):
    q = db.query(Role).filter(
        func.lower(Role.name) == func.lower(name.strip()),
        Role.deleted_at.is_(None),
    )
    if exclude_id:
        q = q.filter(Role.id != exclude_id)
    exists = db.query(q.exists()).scalar()
    if exists:
        raise HTTPException(status_code=409, detail="Role name already exists")

@router.get("/", response_model=PaginatedRoles)
def list_roles(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search by name (icontains)"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    base = db.query(Role).filter(Role.deleted_at.is_(None))
    if not include_inactive:
        base = base.filter(Role.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        base = base.filter(Role.name.ilike(like))
    total = base.count()
    items = (
        base.order_by(Role.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedRoles(total=total, page=page, page_size=page_size, items=items)

@router.get("/{role_id}", response_model=RoleOut)
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    return role

@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db)):
    _assert_unique_name(db, payload.name)
    role = Role(
        name=payload.name.strip(),
        description=(payload.description or "").strip() or None,
        is_active=True if payload.is_active is None else bool(payload.is_active),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

@router.patch("/{role_id}", response_model=RoleOut)
def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    if payload.name is not None and payload.name.strip() != role.name:
        _assert_unique_name(db, payload.name, exclude_id=role.id)
        role.name = payload.name.strip()
    if payload.description is not None:
        role.description = payload.description.strip() or None
    if payload.is_active is not None:
        role.is_active = bool(payload.is_active)
    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)
    return role

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_role(role_id: int, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    role.deleted_at = datetime.utcnow()
    role.updated_at = datetime.utcnow()
    db.commit()
    return None

@router.post("/{role_id}/restore", response_model=RoleOut)
def restore_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role or role.deleted_at is None:
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    role.deleted_at = None
    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)
    return role

@router.post("/{role_id}/toggle", response_model=RoleOut)
def toggle_role_active(role_id: int, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    role.is_active = not bool(role.is_active)
    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)
    return role
