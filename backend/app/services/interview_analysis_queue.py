"""Durable background processing for completed interview assessments."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import exists, select

from app.db.session import SessionLocal
from app.graphs.interview_analysis_graph import interview_analysis_graph
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.models.screening_score import TranscriptSegment
from app.services.screening import extract_resume_text

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
STALE_AFTER = timedelta(minutes=20)
UPLOAD_DIR = Path(os.getenv("CANDIDATE_UPLOAD_DIR", "/data/candidate-resumes"))


class AnalysisInputError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _enqueue_completed_interviews(session, now: datetime) -> None:
    has_transcript = exists().where(TranscriptSegment.interview_id == Interview.id)
    interviews = session.scalars(
        select(Interview).where(
            Interview.status == "completed",
            Interview.analysis_status == "not_started",
            has_transcript,
        )
    ).all()
    for interview in interviews:
        interview.analysis_status = "pending"
        interview.analysis_next_attempt_at = now


def _recover_stale_jobs(session, now: datetime) -> None:
    stale = session.scalars(
        select(Interview).where(
            Interview.analysis_status == "processing",
            Interview.analysis_processing_at < now - STALE_AFTER,
        )
    ).all()
    for interview in stale:
        interview.analysis_processing_at = None
        if interview.analysis_attempts >= MAX_ATTEMPTS:
            interview.analysis_status = "failed"
            interview.analysis_error_code = "ANALYSIS_ATTEMPTS_EXHAUSTED"
            interview.analysis_next_attempt_at = None
        else:
            interview.analysis_status = "pending"
            interview.analysis_next_attempt_at = now


def _claim(interview_id: int, now: datetime) -> int | None:
    with SessionLocal() as session:
        interview = session.scalar(
            select(Interview)
            .where(Interview.id == interview_id)
            .with_for_update(skip_locked=True)
        )
        if (
            interview is None
            or interview.status != "completed"
            or interview.analysis_status != "pending"
            or interview.analysis_attempts >= MAX_ATTEMPTS
            or (interview.analysis_next_attempt_at and interview.analysis_next_attempt_at > now)
        ):
            return None
        interview.analysis_status = "processing"
        interview.analysis_processing_at = now
        interview.analysis_next_attempt_at = None
        interview.analysis_error_code = None
        interview.analysis_attempts += 1
        session.commit()
        return interview.analysis_attempts


def _load_inputs(interview_id: int) -> dict:
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise AnalysisInputError("INTERVIEW_NOT_FOUND")
        _interview, application, job = row
        segments = session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.interview_id == interview_id)
            .order_by(TranscriptSegment.started_at_seconds, TranscriptSegment.id)
        ).all()
        if not segments:
            raise AnalysisInputError("TRANSCRIPT_UNAVAILABLE")
        requirements = session.scalars(
            select(JobRequirement)
            .where(JobRequirement.job_id == job.id)
            .order_by(JobRequirement.id)
        ).all()
        if not requirements:
            raise AnalysisInputError("REQUIREMENTS_UNAVAILABLE")
        resume_path = UPLOAD_DIR / application.resume_storage_key if application.resume_storage_key else None
        resume_filename = application.resume_file_name or "resume.pdf"
        resume_bytes = None
        if resume_path and resume_path.is_file() and resume_path.parent.resolve() == UPLOAD_DIR.resolve():
            resume_bytes = resume_path.read_bytes()

        try:
            resume_text = extract_resume_text(resume_bytes, resume_filename) if resume_bytes else None
        except Exception:
            logger.info("Resume text unavailable for interview assessment %s", interview_id)
            resume_text = None
        return {
            "interview_id": interview_id,
            "segments": [
                {
                    "id": item.id,
                    "speaker_role": item.speaker_role,
                    "started_at_seconds": item.started_at_seconds,
                    "ended_at_seconds": item.ended_at_seconds,
                    "text": item.text,
                }
                for item in segments
            ],
            "requirements": [
                {"text": item.text, "kind": item.kind, "category": item.category, "weight": item.weight}
                for item in requirements
            ],
            "resume_text": resume_text,
        }


def _record_failure(interview_id: int, attempts: int, code: str, now: datetime) -> None:
    with SessionLocal() as session:
        interview = session.get(Interview, interview_id)
        if interview is None:
            return
        interview.analysis_processing_at = None
        interview.analysis_error_code = code[:80]
        if attempts >= MAX_ATTEMPTS:
            interview.analysis_status = "failed"
            interview.analysis_next_attempt_at = None
        else:
            interview.analysis_status = "pending"
            delay_seconds = min(600, 30 * (2 ** (attempts - 1)))
            interview.analysis_next_attempt_at = now + timedelta(seconds=delay_seconds)
        session.commit()


def _process(interview_id: int, attempts: int) -> None:
    try:
        result = interview_analysis_graph.invoke(_load_inputs(interview_id))
        if not result.get("evaluation_id"):
            raise AnalysisInputError("ASSESSMENT_NOT_PERSISTED")
        with SessionLocal() as session:
            interview = session.get(Interview, interview_id)
            if interview is not None and interview.analysis_status == "processing":
                interview.analysis_status = "completed"
                interview.analysis_processing_at = None
                interview.analysis_next_attempt_at = None
                interview.analysis_error_code = None
                session.commit()
    except AnalysisInputError as exc:
        _record_failure(interview_id, attempts, exc.code, datetime.now(timezone.utc))
    except Exception:
        logger.exception("Automatic interview assessment failed for interview %s", interview_id)
        _record_failure(interview_id, attempts, "ASSESSMENT_SERVICE_ERROR", datetime.now(timezone.utc))


def dispatch_pending_interview_analyses(limit: int = 3) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _enqueue_completed_interviews(session, now)
        _recover_stale_jobs(session, now)
        session.commit()
        interview_ids = session.scalars(
            select(Interview.id)
            .where(
                Interview.analysis_status == "pending",
                (Interview.analysis_next_attempt_at.is_(None)) | (Interview.analysis_next_attempt_at <= now),
            )
            .order_by(Interview.analysis_next_attempt_at, Interview.id)
            .limit(limit)
        ).all()

    processed = 0
    for interview_id in interview_ids:
        attempts = _claim(interview_id, datetime.now(timezone.utc))
        if attempts is None:
            continue
        _process(interview_id, attempts)
        processed += 1
    return processed
