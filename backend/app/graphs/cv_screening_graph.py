from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import NotRequired, TypedDict

from pypdf.errors import PdfReadError
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.interview import Interview
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.models.screening_score import ScreeningScore
from app.services.screening import evaluate_resume, extract_resume_text


UPLOAD_DIR = Path(os.getenv("CANDIDATE_UPLOAD_DIR", "/data/candidate-resumes"))
INTERVIEW_SCORE_THRESHOLD = 65.0
MAX_EVALUATION_ATTEMPTS = 3


class ScreeningInputError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CVScreeningState(TypedDict):
    score_id: int
    application_id: NotRequired[int]
    resume_bytes: NotRequired[bytes]
    filename: NotRequired[str]
    requirements: NotRequired[list[dict]]
    job_description: NotRequired[str]
    model_name: NotRequired[str]
    resume_text: NotRequired[str]
    evaluation_attempts: NotRequired[int]
    evaluation_error: NotRequired[str | None]
    result: NotRequired[dict]
    status: NotRequired[str]


def load_application_inputs(state: CVScreeningState) -> dict:
    with SessionLocal() as session:
        row = session.execute(
            select(ScreeningScore, Application, Job)
            .join(Application, Application.id == ScreeningScore.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(ScreeningScore.id == state["score_id"])
        ).first()
        if row is None:
            raise ScreeningInputError("APPLICATION_OR_SCORE_MISSING")

        score, application, job = row
        requirements = session.scalars(
            select(JobRequirement)
            .where(JobRequirement.job_id == job.id)
            .order_by(JobRequirement.id)
        ).all()
        requirement_data = [{
            "text": item.text,
            "kind": item.kind,
            "category": item.category,
            "weight": item.weight,
        } for item in requirements]
        if not requirement_data:
            raise ScreeningInputError("MISSING_REQUIREMENTS")
        if not application.resume_storage_key:
            raise ScreeningInputError("RESUME_NOT_FOUND")

        path = UPLOAD_DIR / application.resume_storage_key
        if not path.is_file() or path.parent.resolve() != UPLOAD_DIR.resolve():
            raise ScreeningInputError("RESUME_NOT_FOUND")
        try:
            resume_bytes = path.read_bytes()
        except OSError as exc:
            raise ScreeningInputError("RESUME_NOT_FOUND") from exc

        from app.services.screening import digest, screening_context_digest

        job_description = job.jd_text or ""
        if digest(resume_bytes) != score.cv_hash:
            raise ScreeningInputError("APPLICATION_INPUTS_CHANGED")
        if screening_context_digest(requirement_data, job_description) != score.requirements_version:
            raise ScreeningInputError("APPLICATION_INPUTS_CHANGED")

        return {
            "application_id": application.id,
            "resume_bytes": resume_bytes,
            "filename": application.resume_file_name or "resume.pdf",
            "requirements": requirement_data,
            "job_description": job_description,
            "model_name": score.model_name,
        }


def extract_cv_text(state: CVScreeningState) -> dict:
    try:
        text = extract_resume_text(state["resume_bytes"], state["filename"])
    except (ValueError, zipfile.BadZipFile, PdfReadError, KeyError) as exc:
        raise ScreeningInputError("RESUME_UNREADABLE") from exc
    return {"resume_text": text}


def evaluate_cv(state: CVScreeningState) -> dict:
    attempts = state.get("evaluation_attempts", 0) + 1
    try:
        result = evaluate_resume(
            state["resume_text"],
            state["requirements"],
            state["model_name"],
            state["job_description"],
        )
    except ValueError as exc:
        # Malformed output, a skipped requirement, or a quote that is not in the CV.
        return {"evaluation_attempts": attempts, "evaluation_error": str(exc)}
    return {"result": result, "evaluation_attempts": attempts, "evaluation_error": None}


def route_evaluation(state: CVScreeningState) -> str:
    if not state.get("evaluation_error"):
        return "persist_cv_assessment"
    if state["evaluation_attempts"] < MAX_EVALUATION_ATTEMPTS:
        return "evaluate_cv"
    return "reject_evaluation"


def reject_evaluation(state: CVScreeningState) -> dict:
    # Not in the queue's permanent-failure set, so the queue retries later with backoff.
    raise ScreeningInputError("SCORING_OUTPUT_INVALID")


def persist_cv_assessment(state: CVScreeningState) -> dict:
    result = state["result"]
    with SessionLocal() as session:
        score = session.get(ScreeningScore, state["score_id"])
        if score is None or score.status != "processing":
            return {"status": "superseded"}

        score.status = "completed"
        score.processing_at = None
        score.next_attempt_at = None
        score.error_code = None
        score.total_score = result["total_score"]
        score.breakdown = result["breakdown"]
        score.justifications = result["justifications"]
        application = session.get(Application, state["application_id"])
        # Batch-imported CVs are scheduled by the hiring manager, never automatically.
        if application is not None and application.scheduling_status != "manual":
            existing_interview = session.scalar(
                select(Interview).where(Interview.application_id == application.id)
            )
            final_or_active_statuses = {
                "selected", "not selected", "rejected", "withdrawn",
                "decision made", "decision available", "interview scheduled",
                "interview completed",
            }
            if existing_interview is None and application.status not in final_or_active_statuses:
                if result["total_score"] > INTERVIEW_SCORE_THRESHOLD:
                    application.status = "selected for interview"
                    application.scheduling_status = "pending"
                    application.scheduling_processing_at = None
                    application.scheduling_next_attempt_at = None
                    application.scheduling_error_code = None
                else:
                    if application.status == "selected for interview":
                        application.status = "submitted"
                    application.scheduling_status = "not_eligible"
                    application.scheduling_processing_at = None
                    application.scheduling_next_attempt_at = None
                    application.scheduling_error_code = None
        session.add(AuditLog(
            actor_user_id=None,
            action="automatic_candidate_screening",
            target_type="application",
            target_id=str(state["application_id"]),
            before_values=None,
            after_values={"score_id": state["score_id"], "total_score": result["total_score"]},
            reason="CV screening was automatically queued when the candidate applied.",
        ))
        session.commit()

    return {"status": "completed"}


def build_cv_screening_graph():
    graph = StateGraph(CVScreeningState)
    graph.add_node("load_application_inputs", load_application_inputs)
    graph.add_node("extract_cv_text", extract_cv_text)
    graph.add_node("evaluate_cv", evaluate_cv)
    graph.add_node("persist_cv_assessment", persist_cv_assessment)
    graph.add_node("reject_evaluation", reject_evaluation)
    graph.add_edge(START, "load_application_inputs")
    graph.add_edge("load_application_inputs", "extract_cv_text")
    graph.add_edge("extract_cv_text", "evaluate_cv")
    graph.add_conditional_edges("evaluate_cv", route_evaluation, {
        "evaluate_cv": "evaluate_cv",
        "persist_cv_assessment": "persist_cv_assessment",
        "reject_evaluation": "reject_evaluation",
    })
    graph.add_edge("persist_cv_assessment", END)
    graph.add_edge("reject_evaluation", END)
    return graph.compile()


cv_screening_graph = build_cv_screening_graph()
