"""Consolidated candidate assessment (F6), shared by the report route and the manager assistant."""
from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.screening_score import InterviewEvaluation, ScreeningScore
from app.models.user import User


def build_consolidated_assessment(application_id: int) -> dict | None:
    """Return the evidence-linked assessment, or None when the application does not exist."""
    with SessionLocal() as session:
        row = session.execute(
            select(Application, Job, User, Interview)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .outerjoin(Interview, Interview.application_id == Application.id)
            .where(Application.id == application_id)
        ).first()
        if row is None:
            return None
        application, job, candidate, interview = row
        cv_score = session.scalar(select(ScreeningScore).where(
            ScreeningScore.application_id == application_id,
            ScreeningScore.status == "completed",
        ).order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc()).limit(1))
        evaluation = session.scalar(select(InterviewEvaluation).where(
            InterviewEvaluation.interview_id == interview.id if interview else False,
            InterviewEvaluation.evaluation_type == "f5_analysis",
        ).order_by(InterviewEvaluation.created_at.desc(), InterviewEvaluation.id.desc()).limit(1)) if interview else None
        extended = session.scalar(select(InterviewEvaluation).where(
            InterviewEvaluation.interview_id == interview.id if interview else False,
            InterviewEvaluation.evaluation_type == "f8_f9_f10",
        ).order_by(InterviewEvaluation.created_at.desc(), InterviewEvaluation.id.desc()).limit(1)) if interview else None
        cv_details = (cv_score.breakdown or {}).get("requirements", []) if cv_score else []
        strengths = [{"requirement": item["requirement"], "evidence": item.get("evidence_quote", ""), "source": "CV"}
                     for item in cv_details if item.get("status") == "met" and item.get("evidence_quote")]
        weaknesses = [{"requirement": item["requirement"], "evidence": item.get("evidence_quote", ""), "source": "CV"}
                      for item in cv_details if item.get("status") in {"partially_met", "unmet"}]
        analysis = evaluation.payload if evaluation else None
        interview_metrics = {}
        if analysis:
            answers = analysis.get("answers", [])
            for dimension in ("relevance", "accuracy", "completeness", "articulation"):
                values = [item[dimension] for item in answers if dimension in item]
                interview_metrics[dimension] = round(sum(values) / len(values), 2) if values else None
            interview_evidence = [{
                "question_segment_ids": item["question_segment_ids"],
                "answer_segment_ids": item["answer_segment_ids"],
                "requirement_names": [
                    job.requirements[index].text
                    for index in item.get("requirement_indexes", [])
                    if 0 <= index < len(job.requirements)
                ],
                "relevance": item.get("relevance"),
                "accuracy": item.get("accuracy"),
                "completeness": item.get("completeness"),
                "articulation": item.get("articulation"),
                "summary": item["evidence_summary"],
            } for item in answers]
            weaknesses.extend({"requirement": f"Interview probe {index + 1}", "evidence": item["evidence_summary"], "source": "transcript segments", "segment_ids": sorted(set(item["question_segment_ids"] + item["answer_segment_ids"]))}
                              for index, item in enumerate(answers) if min(item["relevance"], item["accuracy"], item["completeness"]) <= 2)
        else:
            interview_evidence = []
        rank = None
        if cv_score:
            all_scores = session.scalars(select(ScreeningScore.total_score).join(
                Application, Application.id == ScreeningScore.application_id
            ).where(Application.job_id == job.id, ScreeningScore.status == "completed")).all()
            rank = 1 + sum(1 for score in all_scores if score is not None and score > cv_score.total_score)
        gaps = analysis.get("never_explored_requirements", []) if analysis else [
            {"requirement": item.text, "requirement_index": index}
            for index, item in enumerate(job.requirements)
        ]
        areas_to_verify = [{"requirement": item["requirement"], "reason": "CV evidence is partial or absent"}
                           for item in cv_details if item.get("status") != "met"]
        areas_to_verify.extend({"requirement": item.get("requirement", "Interview coverage"), "reason": "Not explored during the interview"} for item in gaps)
        extended_payload = extended.payload if extended else None
        if extended_payload:
            weaknesses.extend({"requirement": item["claim"], "evidence": item["follow_up_prompt"],
                               "source": "CV claim follow-up", "segment_ids": item["transcript_segment_ids"]}
                              for item in extended_payload.get("f8_claim_verification", [])
                              if item["label"] in {"contradicted", "asserted_but_unverified", "never_discussed"})
            areas_to_verify.extend({"requirement": "Interview quality", "reason": item}
                                   for item in extended_payload.get("f10_quality", {}).get("recommendations", []))
        return {
            "application_id": application.id,
            "candidate_name": application.candidate_name or candidate.full_name,
            "job_id": job.id, "job_title": job.title,
            "cv_assessment": {"score_id": cv_score.id, "score": cv_score.total_score, "rank": rank,
                              "components": cv_score.breakdown, "justifications": cv_score.justifications} if cv_score else None,
            "interview_assessment": {"evaluation_id": evaluation.id, "component_averages": interview_metrics,
                                     "evidence": interview_evidence,
                                     "f9_weighted_total_out_of_100": (extended_payload or {}).get("f9_weighted_total_out_of_100"),
                                     "f9_dimensions": (extended_payload or {}).get("f9_dimensions"),
                                     "f8_claim_verification": (extended_payload or {}).get("f8_claim_verification"),
                                     "f10_quality": (extended_payload or {}).get("f10_quality")} if evaluation else None,
            "overall_position": "CV score available; interview evidence pending" if cv_score and not evaluation else (
                "CV and interview evidence available for human review" if cv_score and evaluation else "Assessment pending"),
            "strengths": strengths, "weaknesses": weaknesses,
            "evidence_gaps": gaps, "areas_to_verify": areas_to_verify,
            "human_review_required": True,
        }
