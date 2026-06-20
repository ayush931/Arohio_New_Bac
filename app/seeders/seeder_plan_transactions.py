from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.UserPlan import UserPlan
from app.models.PlanTransaction import PlanTransaction
from datetime import datetime, UTC
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_plan_transactions():
    db: Session = SessionLocal()
    logger.info("PlanTransaction Seeder started")

    now = datetime.now(UTC)

    try:
        plans = db.query(UserPlan).all()

        for plan in plans:
            existing = db.query(PlanTransaction).filter(
                PlanTransaction.user_plan_id == plan.id
            ).first()

            if existing:
                continue

            transaction = PlanTransaction(
                user_id=plan.user_id,
                user_plan_id=plan.id,
                amount=499.00,
                payment_mode="manual",
                status="success",
                transaction_ref=f"TXN-{plan.id}",
                paid_at=now,
                created_by=1,
                created_at=now,
                updated_at=now
            )

            db.add(transaction)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
        raise

    finally:
        db.close()
        logger.info("PlanTransaction Seeder finished")


if __name__ == "__main__":
    seed_plan_transactions()