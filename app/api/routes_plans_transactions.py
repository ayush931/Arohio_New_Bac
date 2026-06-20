from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.db.database import get_db
from app.models.PlanTransaction import PlanTransaction

router = APIRouter(prefix="/plan-transactions", tags=["Plan Transactions"])


class PlanTransactionCreate(BaseModel):
    user_id: int
    user_plan_id: int
    amount: float
    payment_mode: str
    status: str
    transaction_ref: str | None = None
    paid_at: datetime | None = None
    created_by: int | None = None


class PlanTransactionUpdate(BaseModel):
    amount: float | None = None
    payment_mode: str | None = None
    status: str | None = None
    transaction_ref: str | None = None
    paid_at: datetime | None = None


def serialize_plan_transaction(t: PlanTransaction):
    return {
        "id": t.id,
        "user_id": t.user_id,
        "user_plan_id": t.user_plan_id,
        "amount": t.amount,
        "payment_mode": t.payment_mode,
        "status": t.status,
        "transaction_ref": t.transaction_ref,
        "paid_at": t.paid_at,
        "created_by": t.created_by,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_plan_transaction(payload: PlanTransactionCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()

    txn = PlanTransaction(
        user_id=payload.user_id,
        user_plan_id=payload.user_plan_id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        status=payload.status,
        transaction_ref=payload.transaction_ref,
        paid_at=payload.paid_at,
        created_by=payload.created_by,
        created_at=now,
        updated_at=now
    )

    db.add(txn)
    db.commit()
    db.refresh(txn)
    return serialize_plan_transaction(txn)


@router.get("/", response_model=List[dict])
def list_plan_transactions(db: Session = Depends(get_db)):
    txns = db.query(PlanTransaction).order_by(PlanTransaction.created_at.desc()).all()
    return [serialize_plan_transaction(t) for t in txns]


@router.get("/user/{user_id}", response_model=List[dict])
def list_plan_transactions_by_user(user_id: int, db: Session = Depends(get_db)):
    txns = db.query(PlanTransaction).filter(
        PlanTransaction.user_id == user_id
    ).order_by(PlanTransaction.created_at.desc()).all()
    return [serialize_plan_transaction(t) for t in txns]


@router.get("/{txn_id}")
def get_plan_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(PlanTransaction).filter(PlanTransaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_plan_transaction(txn)


@router.put("/{txn_id}")
def update_plan_transaction(txn_id: int, payload: PlanTransactionUpdate, db: Session = Depends(get_db)):
    txn = db.query(PlanTransaction).filter(PlanTransaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if payload.amount is not None:
        txn.amount = payload.amount

    if payload.payment_mode is not None:
        txn.payment_mode = payload.payment_mode

    if payload.status is not None:
        txn.status = payload.status

    if payload.transaction_ref is not None:
        txn.transaction_ref = payload.transaction_ref

    if payload.paid_at is not None:
        txn.paid_at = payload.paid_at

    txn.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(txn)
    return serialize_plan_transaction(txn)


@router.delete("/{txn_id}")
def delete_plan_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(PlanTransaction).filter(PlanTransaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
    return {"status": "deleted"}