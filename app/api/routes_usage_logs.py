from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.db.database import get_db
from app.models.UsageLog import UsageLog

router = APIRouter(prefix="/usage-logs", tags=["Usage Logs"])


class UsageLogCreate(BaseModel):
    user_id: int
    user_plan_id: int
    type: str
    file_name: str | None = None
    credits_used: int = 1
    reference_id: int | None = None


class UsageLogUpdate(BaseModel):
    type: str | None = None
    file_name: str | None = None
    credits_used: int | None = None
    reference_id: int | None = None


def serialize_usage_log(u: UsageLog):
    return {
        "id": u.id,
        "user_id": u.user_id,
        "user_plan_id": u.user_plan_id,
        "type": u.type,
        "file_name": u.file_name,
        "credits_used": u.credits_used,
        "reference_id": u.reference_id,
        "created_at": u.created_at,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_usage_log(payload: UsageLogCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()

    log = UsageLog(
        user_id=payload.user_id,
        user_plan_id=payload.user_plan_id,
        type=payload.type,
        file_name=payload.file_name,
        credits_used=payload.credits_used,
        reference_id=payload.reference_id,
        created_at=now
    )

    db.add(log)
    db.commit()
    db.refresh(log)
    return serialize_usage_log(log)


@router.get("/", response_model=List[dict])
def list_usage_logs(db: Session = Depends(get_db)):
    logs = db.query(UsageLog).order_by(UsageLog.created_at.desc()).all()
    return [serialize_usage_log(u) for u in logs]


@router.get("/user/{user_id}", response_model=List[dict])
def list_usage_logs_by_user(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(UsageLog).filter(
        UsageLog.user_id == user_id
    ).order_by(UsageLog.created_at.desc()).all()
    return [serialize_usage_log(u) for u in logs]


@router.get("/{log_id}")
def get_usage_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(UsageLog).filter(UsageLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Usage log not found")
    return serialize_usage_log(log)


@router.put("/{log_id}")
def update_usage_log(log_id: int, payload: UsageLogUpdate, db: Session = Depends(get_db)):
    log = db.query(UsageLog).filter(UsageLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Usage log not found")

    if payload.type is not None:
        log.type = payload.type

    if payload.file_name is not None:
        log.file_name = payload.file_name

    if payload.credits_used is not None:
        log.credits_used = payload.credits_used

    if payload.reference_id is not None:
        log.reference_id = payload.reference_id

    db.commit()
    db.refresh(log)
    return serialize_usage_log(log)


@router.delete("/{log_id}")
def delete_usage_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(UsageLog).filter(UsageLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Usage log not found")

    db.delete(log)
    db.commit()
    return {"status": "deleted"}