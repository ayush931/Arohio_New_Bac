# app/api/v1/routes_admin_audits.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

from sqlalchemy import (
    Table, Column, Integer, String, Text, DateTime, Boolean,
    MetaData, select, desc, and_, or_, func
)
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User           # ORM model (has role_id)
from app.models.role import Role           # <-- add: to resolve role name

router = APIRouter(prefix="/admin/audits", tags=["admin-audits"])

# ---- SQLAlchemy Core table for `audits` (columns as in your phpMyAdmin) ----
metadata = MetaData()
audits = Table(
    "audits",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(100), nullable=False),
    Column("actor_user_id", Integer),
    Column("target_user_id", Integer),
    Column("actor_message", Text),
    Column("custom_message", Text),
    Column("is_read", Boolean, nullable=False),
    Column("read_at", DateTime(timezone=True)),
    Column("meta", Text),                       # stored JSON/text
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# ----------------- Schemas -----------------
class AdminAuditOut(BaseModel):
    id: int
    action: str
    actor_user_id: Optional[int]
    target_user_id: Optional[int]
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    target_name: Optional[str] = None
    target_email: Optional[str] = None
    actor_role_name: Optional[str] = None      # <-- added
    target_role_name: Optional[str] = None     # <-- added
    actor_message: Optional[str]
    custom_message: Optional[str]
    message_for_viewer: Optional[str]          # computed
    is_read: bool
    read_at: Optional[datetime]
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

# ----------------- Helpers -----------------
def _load_json(val: Any) -> Optional[Dict[str, Any]]:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return None

def _full_name(u: Optional[User]) -> Optional[str]:
    if not u:
        return None
    first = (u.first_name or "").strip()
    last  = (u.last_name or "").strip()
    nm = (first + " " + last).strip()
    return nm or None

def _resolve_role_name(db: Session, user: Optional[User]) -> Optional[str]:
    """Return role.name using user's role relation or role_id."""
    if not user:
        return None
    # Prefer eager relation if present
    if getattr(user, "role", None) and getattr(user.role, "name", None):
        return user.role.name
    # Fallback to role_id lookup
    rid = getattr(user, "role_id", None)
    if not rid:
        return None
    role = db.query(Role).filter(Role.id == rid).first()
    return getattr(role, "name", None) if role else None

def _msg_for_viewer(
    viewer_user_id: Optional[int],
    actor_user_id: Optional[int],
    actor_message: Optional[str],
    custom_message: Optional[str],
    meta: Optional[Dict[str, Any]]
) -> Optional[str]:
    if viewer_user_id is not None and actor_user_id is not None and viewer_user_id == actor_user_id:
        return actor_message or custom_message
    if isinstance(meta, dict) and bool(meta.get("actor_is_admin")):
        return actor_message or custom_message
    return custom_message or actor_message

def _row_to_out(db: Session, row, viewer_user_id: Optional[int]) -> AdminAuditOut:
    meta = _load_json(row.meta)

    actor: Optional[User] = None
    target: Optional[User] = None
    if row.actor_user_id:
        actor = db.query(User).filter(User.id == row.actor_user_id, User.deleted_at == None).first()
    if row.target_user_id:
        target = db.query(User).filter(User.id == row.target_user_id, User.deleted_at == None).first()

    actor_role_name  = _resolve_role_name(db, actor)
    target_role_name = _resolve_role_name(db, target)

    return AdminAuditOut(
        id=row.id,
        action=row.action,
        actor_user_id=row.actor_user_id,
        target_user_id=row.target_user_id,
        actor_name=_full_name(actor),
        actor_email=(actor.email if actor else None),
        target_name=_full_name(target),
        target_email=(target.email if target else None),
        actor_role_name=actor_role_name,           # <-- filled
        target_role_name=target_role_name,         # <-- filled
        actor_message=row.actor_message,
        custom_message=row.custom_message,
        message_for_viewer=_msg_for_viewer(
            viewer_user_id, row.actor_user_id, row.actor_message, row.custom_message, meta
        ),
        is_read=bool(row.is_read),
        read_at=row.read_at,
        meta=meta,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

# ===========================================================
# 1) GET /admin/audits  -> paginated list with viewer message
#    Pass viewer_user_id from local/sessionStorage _user.id
# ===========================================================
@router.get("/", response_model=List[AdminAuditOut])
def list_audits_admin(
    db: Session = Depends(get_db),
    viewer_user_id: Optional[int] = Query(None, description="current viewer user id (from _user.id)"),
    q: Optional[str] = Query(None, description="search action/actor_message/custom_message"),
    actor_user_id: Optional[int] = Query(None),
    target_user_id: Optional[int] = Query(None),
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    where = []
    if actor_user_id is not None:
        where.append(audits.c.actor_user_id == actor_user_id)
    if target_user_id is not None:
        where.append(audits.c.target_user_id == target_user_id)
    if is_read is not None:
        where.append(audits.c.is_read == is_read)
    if q:
        like = f"%{q}%"
        where.append(or_(
            audits.c.action.like(like),
            audits.c.actor_message.like(like),
            audits.c.custom_message.like(like),
        ))

    stmt = select(audits)
    if where:
        stmt = stmt.where(and_(*where))
    stmt = stmt.order_by(desc(audits.c.created_at)).offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).fetchall()
    return [_row_to_out(db, r, viewer_user_id) for r in rows]

# ===========================================================
# 2) GET /admin/audits/{audit_id} -> single row
# ===========================================================
@router.get("/{audit_id}", response_model=AdminAuditOut)
def get_audit_admin(
    audit_id: int,
    db: Session = Depends(get_db),
    viewer_user_id: Optional[int] = Query(None),
):
    row = db.execute(select(audits).where(audits.c.id == audit_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")
    return _row_to_out(db, row, viewer_user_id)

# ===========================================================
# 3) GET /admin/audits/for-user/{user_id}
#    all audits where user is actor or target
# ===========================================================
@router.get("/for-user/{user_id}", response_model=List[AdminAuditOut])
def list_audits_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    viewer_user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = (
        select(audits)
        .where(or_(audits.c.actor_user_id == user_id, audits.c.target_user_id == user_id))
        .order_by(desc(audits.c.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).fetchall()
    return [_row_to_out(db, r, viewer_user_id) for r in rows]

# ===========================================================
# 4) GET /admin/audits/unread/count
#    unread count (optionally scoped to viewer: actor or target)
# ===========================================================
@router.get("/unread/count")
def unread_count(
    db: Session = Depends(get_db),
    viewer_user_id: Optional[int] = Query(None, description="if provided, counts rows where viewer is actor or target"),
):
    stmt = select(func.count()).select_from(audits).where(audits.c.is_read == False)
    if viewer_user_id is not None:
        stmt = stmt.where(or_(audits.c.actor_user_id == viewer_user_id, audits.c.target_user_id == viewer_user_id))
    cnt = db.execute(stmt).scalar_one()
    return {"unread": int(cnt)}
