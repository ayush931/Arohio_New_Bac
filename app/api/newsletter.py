# app/api/v1/routes_newsletter.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional, Tuple

from app.core.database import get_db
from app.models.newsletter import Newsletter
from app.models.audit import Audit
from app.models.user import User  

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


def _serialize(obj: Newsletter):
    d: Dict[str, Any] = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        d[c.name] = v.isoformat() if hasattr(v, "isoformat") else v
    return d


# ----------------- actor helpers -----------------
def _actor_from_headers_or_body(request: Request, payload: Optional[dict]) -> Tuple[Optional[int], Optional[str]]:
    """Try headers first, then body fields (actor_user_id / actor_name)."""
    actor_id_hdr = request.headers.get("X-Actor-Id")
    actor_name_hdr = request.headers.get("X-Actor-Name")

    actor_id: Optional[int] = None
    if actor_id_hdr:
        try:
            actor_id = int(actor_id_hdr)
        except Exception:
            actor_id = None

    if actor_id is None and payload:
        try:
            actor_id = int(payload.get("actor_user_id")) if payload.get("actor_user_id") is not None else None
        except Exception:
            actor_id = None

    actor_name = actor_name_hdr or (payload.get("actor_name") if payload else None)
    return actor_id, actor_name


def _actor_full_name(u: User) -> str:
    parts = [u.first_name or "", u.last_name or ""]
    full = " ".join([p for p in parts if p]).strip()
    return full or (getattr(u, "name", None) or "")


def _resolve_actor(db: Session, request: Request, payload: Optional[dict]) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve actor id/name in this order:
    1) X-Actor-Id / X-Actor-Name headers or body fields
    2) If missing but payload.email matches a user -> use that user's id and full name
    """
    actor_id, actor_name = _actor_from_headers_or_body(request, payload)

    if (not actor_id or not actor_name) and payload:
        email = (payload.get("email") or "").strip().lower()
        if email:
            u = db.query(User).filter(User.email == email).first()
            if u:
                if not actor_id:
                    actor_id = int(u.id)
                if not actor_name:
                    actor_name = _actor_full_name(u) or u.email

    return actor_id, actor_name


# ----------------- audit helpers -----------------
def _audit_messages(action: str, actor_name: Optional[str]) -> Tuple[str, str]:
    who = actor_name or "User"
    if action == "subscribe":
        return (f"{who} has successfully subscribed to the newsletter.", "You are now subscribed to the newsletter.")
    if action == "unsubscribe":
        return (f"{who} has unsubscribed from the newsletter.", "You have unsubscribed from the newsletter.")
    if action == "resubscribe":
        return (f"{who} has re-subscribed to the newsletter.", "You have re-subscribed to the newsletter.")
    if action == "update_subscription":
        return (f"{who} updated their newsletter preferences.", "Your newsletter preferences were updated.")
    if action == "delete_subscription":
        return (f"{who} deleted their newsletter subscription.", "Your newsletter subscription was deleted.")
    return (f"{who} performed '{action}' on newsletter.", "Your newsletter settings changed.")


def _write_audit(
    db: Session,
    *,
    actor_user_id: Optional[int],
    actor_name: Optional[str],
    action: str,
    meta: Optional[Dict[str, Any]] = None,
    target_user_id: Optional[int] = None,
):
    """
    Insert an Audit row using your table's actual columns:
      id, action, actor_user_id, target_user_id, actor_message, custom_message, is_read, read_at, meta, created_at, updated_at
    """
    if not actor_user_id:
        return  # skip for anonymous

    actor_msg, custom_msg = _audit_messages(action, actor_name)

    row = Audit(
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,   # often None for newsletter events
        actor_message=actor_msg,
        custom_message=custom_msg,
        is_read=0,
        meta=meta or {},                 # JSON column
    )
    db.add(row)
    # caller will commit


# ----------------- routes -----------------
@router.get("/")
def list_newsletters(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(None),
):
    print("[GET] /newsletters called with status_filter =", status_filter)
    q = db.query(Newsletter)
    if status_filter:
        q = q.filter(Newsletter.status == status_filter)
    rows = q.order_by(Newsletter.id.desc()).all()
    print(f"[GET] returning {len(rows)} rows")
    return [_serialize(x) for x in rows]


@router.get("/{newsletter_id}")
def get_newsletter(newsletter_id: int, db: Session = Depends(get_db)):
    print("[GET] /newsletters/", newsletter_id)
    row = db.query(Newsletter).get(newsletter_id)
    if not row:
        print("[GET] newsletter not found:", newsletter_id)
        raise HTTPException(404, detail="Newsletter not found")
    print("[GET] returning newsletter:", row.email)
    return _serialize(row)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_newsletter(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    print("[POST] /newsletters payload =", payload)
    email = (payload.get("email") or "").strip().lower()
    if not email:
        print("[POST] missing email")
        raise HTTPException(400, detail="Email is required")

    existing = db.query(Newsletter).filter(Newsletter.email == email).first()
    if existing:
        print("[POST] email already subscribed:", email)
        raise HTTPException(400, detail="Email already subscribed")

    # resolve actor (and name) now
    actor_user_id, actor_name = _resolve_actor(db, request, payload)

    # build newsletter row (attach user_id if your model has it)
    create_kwargs: Dict[str, Any] = dict(
        email=email,
        name=payload.get("name"),
        status=payload.get("status") or "subscribed",
        token=payload.get("token"),
        ip_address=payload.get("ip_address"),
        source=payload.get("source"),
    )
    if hasattr(Newsletter, "user_id"):
        create_kwargs["user_id"] = actor_user_id

    row = Newsletter(**create_kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    print("[POST] created newsletter id =", row.id, "email =", row.email)

    # AUDIT (subscribe)
    _write_audit(
        db,
        actor_user_id=actor_user_id,
        actor_name=actor_name,
        action="subscribe",
        target_user_id=None,  # you said no target user id needed
        meta={
            "email": row.email,
            "status": row.status,
            "ip_address": row.ip_address,
            "source": row.source,
            **({"user_id": actor_user_id} if actor_user_id else {}),
        },
    )
    db.commit()

    return _serialize(row)


@router.put("/{newsletter_id}")
def update_newsletter(
    newsletter_id: int,
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    print("[PUT] /newsletters/", newsletter_id, "payload =", payload)
    row = db.query(Newsletter).get(newsletter_id)
    if not row:
        print("[PUT] newsletter not found:", newsletter_id)
        raise HTTPException(404, detail="Newsletter not found")

    prev_status = row.status

    # resolve actor for update (use row.email if not provided)
    actor_user_id, actor_name = _resolve_actor(db, request, {**payload, "email": row.email})

    # apply updates
    for field in ["name", "status", "token", "ip_address", "source"]:
        if field in payload and payload[field] is not None:
            setattr(row, field, payload[field])

    # keep user_id in sync if the model supports it
    if hasattr(Newsletter, "user_id") and actor_user_id:
        row.user_id = actor_user_id

    db.add(row)
    db.commit()
    db.refresh(row)
    print("[PUT] updated newsletter id =", row.id)

    # decide audit action
    action = "update_subscription"
    if "status" in payload and payload["status"] is not None:
        new_status = str(payload["status"]).lower()
        prev = (prev_status or "").lower()
        if prev != new_status:
            if new_status == "subscribed" and prev == "unsubscribed":
                action = "resubscribe"
            elif new_status == "subscribed":
                action = "subscribe"
            elif new_status == "unsubscribed":
                action = "unsubscribe"

    _write_audit(
        db,
        actor_user_id=actor_user_id,
        actor_name=actor_name,
        action=action,
        target_user_id=None,
        meta={
            "email": row.email,
            "status": row.status,
            "previous_status": prev_status,
            "ip_address": row.ip_address,
            "source": row.source,
            **({"user_id": actor_user_id} if actor_user_id else {}),
        },
    )
    db.commit()

    return _serialize(row)


@router.delete("/{newsletter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_newsletter(
    newsletter_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    print("[DELETE] /newsletters/", newsletter_id)
    row = db.query(Newsletter).get(newsletter_id)
    if not row:
        print("[DELETE] newsletter not found:", newsletter_id)
        raise HTTPException(404, detail="Newsletter not found")

    # resolve actor (use row.email to backfill)
    actor_user_id, actor_name = _resolve_actor(db, request, {"email": row.email})

    # snapshot for audit meta
    meta = {
        "email": row.email,
        "status": row.status,
        "ip_address": row.ip_address,
        "source": row.source,
        **({"user_id": actor_user_id} if actor_user_id else {}),
    }

    db.delete(row)
    db.commit()
    print("[DELETE] deleted newsletter id =", newsletter_id)

    _write_audit(
        db,
        actor_user_id=actor_user_id,
        actor_name=actor_name,
        action="delete_subscription",
        target_user_id=None,
        meta=meta,
    )
    db.commit()

    return None
