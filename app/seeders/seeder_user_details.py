from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from passlib.hash import bcrypt
from datetime import datetime, UTC
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_admin():
    db: Session = SessionLocal()
    logger.info("Seeder started")

    existing = db.query(User).filter(User.email == "admin@yopmail.com").first()
    if existing:
        logger.info("Admin already exists")
        return

    logger.info("Creating admin user")

    admin = User(
        first_name="Admin",
        last_name="User",
        email="admin@yopmail.com",
        password_hash=bcrypt.hash("Admin@123"),
        role_id=2,
        locale="en",
        time_zone="Asia/Kolkata",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    db.add(admin)
    db.commit()

    logger.info(f"Admin created with ID: {admin.id}")

    db.close()
    logger.info("Seeder finished")


if __name__ == "__main__":
    seed_admin()