from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.UserPlan import UserPlan
from app.models.UsageLog import UsageLog
from datetime import datetime, UTC
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_usage_logs():
    db: Session = SessionLocal()
    logger.info("UsageLog Seeder started")

    now = datetime.now(UTC)

    try:
        plans = db.query(UserPlan).all()

        for plan in plans:
            existing = db.query(UsageLog).filter(
                UsageLog.user_plan_id == plan.id
            ).first()

            if existing:
                continue

            log = UsageLog(
                user_id=plan.user_id,
                user_plan_id=plan.id,
                type="pdf",
                file_name=f"file_{plan.id}.pdf",
                credits_used=1,
                reference_id=None,
                created_at=now
            )

            db.add(log)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
        raise

    finally:
        db.close()
        logger.info("UsageLog Seeder finished")


if __name__ == "__main__":
    seed_usage_logs()