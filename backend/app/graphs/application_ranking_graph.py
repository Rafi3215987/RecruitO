from __future__ import annotations

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.job import Job
from app.models.screening_score import ScreeningScore


class ApplicationRankingState(TypedDict):
    job_id: int
    job_title: NotRequired[str]
    applications: NotRequired[list[dict]]


def load_job_applicants(state: ApplicationRankingState) -> dict:
    with SessionLocal() as session:
        job = session.get(Job, state["job_id"])
        applications = session.scalars(
            select(Application)
            .where(Application.job_id == state["job_id"], Application.status != "withdrawn")
            .order_by(Application.created_at, Application.id)
        ).all()

        rows = []
        for application in applications:
            score = session.scalar(
                select(ScreeningScore)
                .where(ScreeningScore.application_id == application.id)
                .order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc())
                .limit(1)
            )
            rows.append({
                "application_id": application.id,
                "candidate_name": application.candidate_name or "Candidate",
                "status": score.status if score else "not_started",
                "total_score": score.total_score if score else None,
                "breakdown": score.breakdown if score else None,
                "justifications": score.justifications if score else None,
                "score_id": score.id if score else None,
            })

        return {"job_title": job.title if job else "", "applications": rows}


def rank_applicants(state: ApplicationRankingState) -> dict:
    applications = state.get("applications", [])

    def tiebreak(applicant: dict, category: str) -> float:
        requirements = (applicant.get("breakdown") or {}).get("requirements", [])
        return sum(
            item.get("score", 0)
            for item in requirements
            if item.get("category") == category
        )

    applications.sort(key=lambda item: (
        item["status"] != "completed",
        -(item["total_score"] or 0),
        -tiebreak(item, "skills"),
        -tiebreak(item, "experience"),
        item["candidate_name"].casefold(),
    ))

    for index, applicant in enumerate(applications, start=1):
        applicant["rank"] = index if applicant["status"] == "completed" else None

    return {"applications": applications}


def build_application_ranking_graph():
    graph = StateGraph(ApplicationRankingState)
    graph.add_node("load_job_applicants", load_job_applicants)
    graph.add_node("rank_applicants", rank_applicants)
    graph.add_edge(START, "load_job_applicants")
    graph.add_edge("load_job_applicants", "rank_applicants")
    graph.add_edge("rank_applicants", END)
    return graph.compile()


application_ranking_graph = build_application_ranking_graph()
