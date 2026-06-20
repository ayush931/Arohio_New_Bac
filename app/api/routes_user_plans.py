from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.db.database import get_db
from app.models.UserPlan import UserPlan

router = APIRouter(prefix="/user-plans", tags=["User Plans"])


# =========================
# SCHEMAS
# =========================

class UserPlanCreate(BaseModel):
    user_id: int
    plan_name: str | None = None
    pdf_limit: int
    image_limit: int
    start_date: datetime
    end_date: datetime
    assigned_by: int | None = None


class UserPlanUpdate(BaseModel):
    plan_name: str | None = None
    pdf_limit: int | None = None
    image_limit: int | None = None
    pdf_used: int | None = None
    image_used: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool | None = None


# =========================
# SERIALIZER
# =========================

def serialize_user_plan(p: UserPlan):
    return {
        "id": p.id,
        "user_id": p.user_id,
        "plan_name": p.plan_name,
        "pdf_limit": p.pdf_limit,
        "image_limit": p.image_limit,
        "pdf_used": p.pdf_used,
        "image_used": p.image_used,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "is_active": p.is_active,
        "assigned_by": p.assigned_by,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


# =========================
# CREATE
# =========================

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user_plan(payload: UserPlanCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()

    # deactivate old active plans (optional but practical)
    db.query(UserPlan).filter(
        UserPlan.user_id == payload.user_id,
        UserPlan.is_active.is_(True)
    ).update({"is_active": False})

    plan = UserPlan(
        user_id=payload.user_id,
        plan_name=payload.plan_name,
        pdf_limit=payload.pdf_limit,
        image_limit=payload.image_limit,
        pdf_used=0,
        image_used=0,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=True,
        assigned_by=payload.assigned_by,
        created_at=now,
        updated_at=now
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return serialize_user_plan(plan)


# =========================
# LIST ALL
# =========================

@router.get("/", response_model=List[dict])
def list_user_plans(db: Session = Depends(get_db)):
    plans = db.query(UserPlan).order_by(UserPlan.created_at.desc()).all()
    return [serialize_user_plan(p) for p in plans]


# =========================
# LIST BY USER
# =========================

@router.get("/user/{user_id}", response_model=List[dict])
def list_user_plans_by_user(user_id: int, db: Session = Depends(get_db)):
    plans = db.query(UserPlan).filter(
        UserPlan.user_id == user_id
    ).order_by(UserPlan.created_at.desc()).all()
    return [serialize_user_plan(p) for p in plans]


# =========================
# GET ONE
# =========================

@router.get("/{plan_id}")
def get_user_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(UserPlan).filter(UserPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="User plan not found")
    return serialize_user_plan(plan)


# =========================
# UPDATE
# =========================

@router.put("/{plan_id}")
def update_user_plan(plan_id: int, payload: UserPlanUpdate, db: Session = Depends(get_db)):
    plan = db.query(UserPlan).filter(UserPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="User plan not found")

    new_pdf_limit = payload.pdf_limit if payload.pdf_limit is not None else plan.pdf_limit
    new_image_limit = payload.image_limit if payload.image_limit is not None else plan.image_limit

    new_pdf_used = payload.pdf_used if payload.pdf_used is not None else plan.pdf_used
    new_image_used = payload.image_used if payload.image_used is not None else plan.image_used

    if new_pdf_limit < new_pdf_used:
        raise HTTPException(status_code=400, detail="PDF limit cannot be less than usage")

    if new_image_limit < new_image_used:
        raise HTTPException(status_code=400, detail="Image limit cannot be less than usage")

    if payload.plan_name is not None:
        plan.plan_name = payload.plan_name

    if payload.pdf_limit is not None:
        plan.pdf_limit = payload.pdf_limit

    if payload.image_limit is not None:
        plan.image_limit = payload.image_limit

    if payload.pdf_used is not None:
        plan.pdf_used = payload.pdf_used

    if payload.image_used is not None:
        plan.image_used = payload.image_used

    if payload.start_date is not None:
        plan.start_date = payload.start_date

    if payload.end_date is not None:
        plan.end_date = payload.end_date

    if payload.is_active is not None:
        plan.is_active = payload.is_active

    plan.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(plan)
    return serialize_user_plan(plan)
# =========================
# DELETE
# =========================

@router.delete("/{plan_id}")
def delete_user_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(UserPlan).filter(UserPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="User plan not found")

    db.delete(plan)
    db.commit()
    return {"status": "deleted"}