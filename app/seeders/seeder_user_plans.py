from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.UserPlan import UserPlan
from datetime import datetime, timedelta, UTC
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_user_plans():
    db: Session = SessionLocal()
    logger.info("UserPlan Seeder started")

    now = datetime.now(UTC)

    for user_id in range(1, 11):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue

        existing = db.query(UserPlan).filter(
            UserPlan.user_id == user_id,
            UserPlan.is_active.is_(True)
        ).first()

        if existing:
            continue

        plan = UserPlan(
            user_id=user_id,
            plan_name=f"Plan-{user_id}",
            pdf_limit=100,
            image_limit=500,
            pdf_used=0,
            image_used=0,
            start_date=now,
            end_date=now + timedelta(days=30),
            is_active=True,
            assigned_by=1,
            created_at=now,
            updated_at=now
        )

        db.add(plan)

    db.commit()
    db.close()
    logger.info("UserPlan Seeder finished")


if __name__ == "__main__":
    seed_user_plans()