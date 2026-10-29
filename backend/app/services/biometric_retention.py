from datetime import datetime, timezone

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.screening_score import BiometricEnrollment


def delete_expired_biometric_enrollments() -> int:
    """Delete face representations when their stated 30-day retention ends."""
    with SessionLocal() as session:
        result = session.execute(delete(BiometricEnrollment).where(
            BiometricEnrollment.retention_until <= datetime.now(timezone.utc)
        ))
        session.commit()
        return int(result.rowcount or 0)
