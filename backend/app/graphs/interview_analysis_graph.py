from __future__ import annotations

import logging
import os
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.db.session import SessionLocal
from app.models.screening_score import InterviewEvaluation
from app.services.extended_assessment import evaluate_extended_assessment
from app.services.interview_analysis import analyze_transcript, validate_interview_analysis


class InterviewAnalysisState(TypedDict):
    interview_id: int
    segments: list[dict]
    requirements: list[dict]
    resume_text: str | None
    analysis: NotRequired[dict]
    validation: NotRequired[dict]
    evaluation_id: NotRequired[int]
    extended_assessment: NotRequired[dict | None]
    extended_assessment_status: NotRequired[str]


def analyze_f5(state: InterviewAnalysisState) -> dict:
    return {"analysis": analyze_transcript(state["segments"], state["requirements"])}


def validate_f5(state: InterviewAnalysisState) -> dict:
    validation = validate_interview_analysis(state["analysis"], state["requirements"])
    update: dict = {"validation": validation}
    if validation["status"] != "passed":
        update["extended_assessment"] = None
        update["extended_assessment_status"] = "skipped_insufficient_analysis"
    return update


def persist_f5(state: InterviewAnalysisState) -> dict:
    with SessionLocal() as session:
        row = InterviewEvaluation(
            interview_id=state["interview_id"], evaluation_type="f5_analysis",
            payload={**state["analysis"], "validation": state.get("validation")},
            model_name=os.getenv("ASSESSMENT_MODEL", "gemini-3-flash-preview"),
            prompt_version="interview-analysis-v1",
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"evaluation_id": row.id}


def route_extended(state: InterviewAnalysisState) -> str:
    if state.get("validation", {}).get("status") != "passed":
        return END
    return "evaluate_f8_f9_f10" if state.get("resume_text") else END


def evaluate_extended(state: InterviewAnalysisState) -> dict:
    try:
        result = evaluate_extended_assessment(
            state["resume_text"] or "", state["segments"],
            state["requirements"], state["analysis"],
        )
        with SessionLocal() as session:
            session.add(InterviewEvaluation(
                interview_id=state["interview_id"], evaluation_type="f8_f9_f10",
                payload=result, model_name=os.getenv("ASSESSMENT_MODEL", "gemini-3-flash-preview"),
                prompt_version="extended-interview-assessment-v1",
            ))
            session.commit()
        return {"extended_assessment": result, "extended_assessment_status": "completed"}
    except Exception:
        logging.getLogger(__name__).exception(
            "Extended interview assessment failed for interview %s", state["interview_id"]
        )
        return {"extended_assessment": None, "extended_assessment_status": "failed"}


def build_interview_analysis_graph():
    graph = StateGraph(InterviewAnalysisState)
    graph.add_node("analyze_f5", analyze_f5)
    graph.add_node("validate_f5", validate_f5)
    graph.add_node("persist_f5", persist_f5)
    graph.add_node("evaluate_f8_f9_f10", evaluate_extended)
    graph.add_edge(START, "analyze_f5")
    graph.add_edge("analyze_f5", "validate_f5")
    graph.add_edge("validate_f5", "persist_f5")
    graph.add_conditional_edges("persist_f5", route_extended,
                                {"evaluate_f8_f9_f10": "evaluate_f8_f9_f10", END: END})
    graph.add_edge("evaluate_f8_f9_f10", END)
    return graph.compile()


interview_analysis_graph = build_interview_analysis_graph()
