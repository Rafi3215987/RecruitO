import os

from dotenv import load_dotenv
from pwdlib import PasswordHash
from sqlalchemy import select

load_dotenv()

from app.db.session import SessionLocal
from app.models.user import User


password_hasher = PasswordHash.recommended()


def main() -> None:
    email = os.getenv("HIRING_MANAGER_EMAIL")
    password = os.getenv("HIRING_MANAGER_PASSWORD")
    full_name = os.getenv("HIRING_MANAGER_NAME")

    if not email or not password or not full_name:
        raise RuntimeError("Hiring-manager seed settings are incomplete")

    with SessionLocal() as session:
        existing_user = session.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            if existing_user.role != "hiring_manager":
                raise RuntimeError(
                    "The configured hiring-manager email belongs to another role"
                )

            print("Hiring-manager account already exists; skipped.")
            return

        user = User(
            email=email,
            password_hash=password_hasher.hash(password),
            role="hiring_manager",
            full_name=full_name,
            is_active=True,
        )
        session.add(user)
        session.commit()

    print("Hiring-manager account created.")


if __name__ == "__main__":
    main()