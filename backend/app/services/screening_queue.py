from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.graphs.cv_screening_graph import ScreeningInputError, cv_screening_graph
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.job_requirement import JobRequirement
from app.models.screening_score import ScreeningScore
from app.services.screening import PROMPT_VERSION, digest, screening_context_digest


logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
SCREENING_CONCURRENCY = max(1, int(os.getenv("SCREENING_CONCURRENCY", "4")))


def requirement_data_for_job(session, job_id: int) -> list[dict]:
    """Requirements in the stable order every scoring version is keyed on."""
    requirements = session.scalars(
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .order_by(JobRequirement.id)
    ).all()
    return [{
        "text": item.text,
        "kind": item.kind,
        "category": item.category,
        "weight": item.weight,
    } for item in requirements]


def enqueue_application_screening(
    session,
    application: Application,
    resume_bytes: bytes,
    requirements: list[dict],
    job_description: str = "",
) -> ScreeningScore:
    model_name = os.getenv("SCORING_MODEL", "gemini-3.1-flash-lite")
    requirements_version = screening_context_digest(requirements, job_description)
    cv_hash = digest(resume_bytes)
    score = session.scalar(select(ScreeningScore).where(
        ScreeningScore.application_id == application.id,
        ScreeningScore.cv_hash == cv_hash,
        ScreeningScore.requirements_version == requirements_version,
        ScreeningScore.prompt_version == PROMPT_VERSION,
        ScreeningScore.model_name == model_name,
    ))
    if score is not None:
        if score.status == "failed" and requirements:
            score.status = "pending"
            score.error_code = None
            score.attempts = 0
            score.processing_at = None
            score.next_attempt_at = None
        return score

    score = ScreeningScore(
        application_id=application.id,
        cv_hash=cv_hash,
        requirements_version=requirements_version,
        prompt_version=PROMPT_VERSION,
        model_name=model_name,
        status="pending" if requirements else "failed",
        error_code=None if requirements else "MISSING_REQUIREMENTS",
    )
    session.add(score)
    return score


def _recover_stale_screenings(now: datetime) -> None:
    with SessionLocal() as session:
        stale = session.scalars(select(ScreeningScore).where(
            ScreeningScore.status == "processing",
            (ScreeningScore.processing_at.is_(None))
            | (ScreeningScore.processing_at < now - timedelta(minutes=15)),
        )).all()
        for score in stale:
            score.processing_at = None
            if score.attempts >= MAX_ATTEMPTS:
                score.status = "failed"
                score.error_code = "SCORING_ATTEMPTS_EXHAUSTED"
            else:
                score.status = "pending"
                score.next_attempt_at = now
        if stale:
            session.commit()


def _claim_screening(score_id: int, now: datetime) -> int | None:
    with SessionLocal() as session:
        score = session.scalar(
            select(ScreeningScore)
            .where(ScreeningScore.id == score_id)
            .with_for_update(skip_locked=True)
        )
        if (
            score is None
            or score.status != "pending"
            or score.attempts >= MAX_ATTEMPTS
            or (score.next_attempt_at is not None and score.next_attempt_at > now)
        ):
            return None
        score.status = "processing"
        score.processing_at = now
        score.next_attempt_at = None
        score.attempts += 1
        session.commit()
        return score.attempts


def _record_failure(score_id: int, attempts: int, error_code: str, now: datetime) -> None:
    with SessionLocal() as session:
        score = session.get(ScreeningScore, score_id)
        if score is None:
            return
        score.processing_at = None
        score.error_code = error_code
        if attempts >= MAX_ATTEMPTS or error_code in {
            "APPLICATION_OR_SCORE_MISSING",
            "MISSING_REQUIREMENTS",
            "RESUME_NOT_FOUND",
            "RESUME_UNREADABLE",
            "APPLICATION_INPUTS_CHANGED",
        }:
            score.status = "failed"
            score.next_attempt_at = None
        else:
            score.status = "pending"
            delay_seconds = min(30 * (2 ** max(attempts - 1, 0)), 300)
            score.next_attempt_at = now + timedelta(seconds=delay_seconds)
        session.commit()


def _process_screening(score_id: int, attempts: int) -> None:
    try:
        result = cv_screening_graph.invoke({"score_id": score_id})
        if result.get("status") == "superseded":
            logger.info("Screening result %s was superseded before persistence", score_id)
    except ScreeningInputError as exc:
        _record_failure(score_id, attempts, exc.code, datetime.now(timezone.utc))
    except Exception:
        logger.exception("Automatic CV scoring failed for score record %s", score_id)
        _record_failure(score_id, attempts, "SCORING_SERVICE_ERROR", datetime.now(timezone.utc))


def dispatch_pending_screenings(limit: int = 20) -> int:
    """Claim due screenings and run them on a small thread pool.

    Each graph run opens its own database sessions, so runs are independent;
    the pool bounds concurrent LLM calls for batch imports (N1).
    """
    now = datetime.now(timezone.utc)
    _recover_stale_screenings(now)
    with SessionLocal() as session:
        ids = session.scalars(
            select(ScreeningScore.id)
            .where(
                ScreeningScore.status == "pending",
                ScreeningScore.attempts < MAX_ATTEMPTS,
                (ScreeningScore.next_attempt_at.is_(None))
                | (ScreeningScore.next_attempt_at <= now),
            )
            .order_by(ScreeningScore.created_at.asc())
            .limit(limit)
        ).all()
    claimed = []
    for score_id in ids:
        attempts = _claim_screening(score_id, datetime.now(timezone.utc))
        if attempts is not None:
            claimed.append((score_id, attempts))
    if not claimed:
        return 0
    with ThreadPoolExecutor(max_workers=min(SCREENING_CONCURRENCY, len(claimed))) as pool:
        list(pool.map(lambda item: _process_screening(*item), claimed))
    return len(claimed)
