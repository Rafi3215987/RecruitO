

import os
from dotenv import load_dotenv
from google import genai
from typing import NotRequired, TypedDict
from langgraph.graph import END, START, StateGraph
from typing import Literal
from pydantic import BaseModel, Field
from google.genai import types

from app.db.session import SessionLocal
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.services.policy_retrieval import retrieve_policy


load_dotenv()


class _LazyGeminiClient:
    """Build the Gemini client on first use, so the API still starts without a key (N6)."""

    _client = None

    @property
    def models(self):
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            type(self)._client = genai.Client(api_key=api_key)
        return self._client.models


client = _LazyGeminiClient()

class JDState(TypedDict):
    role_title: str
    seniority: str
    key_skills: list[str]
    employment_type: str
    location_mode: str
    jd_text: NotRequired[str]
    requirements: NotRequired[list[dict[str, str | int]]]
    job_id: NotRequired[int]
    policy_context: NotRequired[list[dict[str, str]]]
    issues: NotRequired[list[str]]
    retry_count: NotRequired[int]
    additional_details: NotRequired[str]
    created_by_id: int

BANNED_PHRASES = (
    "young, energetic",
    "young and energetic",
    "young candidate",
    "male candidates only",
    "female candidates only",
    "native english speaker",
)

PROTECTED_CHARACTERISTIC_PHRASES = (
    "young",
    "old",
    "male candidates only",
    "female candidates only",
    "native english speaker",
    "nationality requirement",
    "marital status",
    "married",
    "unmarried",
)

MAX_POLICY_RETRIES = 2

REQUIRED_CONTENT = {
    "role summary": ("role summary", "about the role", "overview"),
    "responsibilities": (
        "responsibilities",
        "what you'll do",
        "what you will do",
    ),
    "required qualifications": (
        "required qualifications",
        "minimum qualifications",
        "required skills",
    ),
    "work location or mode": (
        "work location",
        "work mode",
        "remote",
        "hybrid",
        "on site",
    ),
    "equal-opportunity statement": (
        "equal opportunity",
        "equal employment opportunity",
    ),
}

class Requirement(BaseModel):
    text: str
    kind: Literal["required", "preferred"]
    category: Literal["skills", "experience", "qualification"]
    weight: int = Field(ge=1, le=5)


class RequirementsResponse(BaseModel):
    requirements: list[Requirement]

def retrieve_policy_node(state: JDState) -> dict:
    query = (
        f"Role: {state['role_title']}\n"
        f"Seniority: {state['seniority']}\n"
        f"Skills: {', '.join(state['key_skills'])}\n"
        f"Employment type: {state['employment_type']}\n"
        f"Location mode: {state['location_mode']}\n"
        f"Additional hiring-manager requirements: "
        f"{state.get('additional_details', '')}"
    )

    return {"policy_context": retrieve_policy(query, k=3)}

def draft_jd(state: JDState) -> dict:
    policy_text = "\n\n".join(
        f"Source: {policy['source']} | Section: {policy['heading']}\n"
        f"{policy['content']}"
        for policy in state.get("policy_context", [])
    )

    issues = state.get("issues", [])
    retry_feedback = ""
    if issues:
        retry_feedback = (
            "\nFix these issues from the previous draft:\n"
            + "\n".join(f"- {issue}" for issue in issues)
        )

    prompt = f"""
Write a clear job description using these details:
Role: {state["role_title"]}
Seniority: {state["seniority"]}
Key skills: {", ".join(state["key_skills"])}
Employment type: {state["employment_type"]}
Location mode: {state["location_mode"]}
Additional requirements and role context from the hiring manager:
{state.get("additional_details", "None provided")}

Follow these hiring policies:
{policy_text}

{retry_feedback}

Return only the job description text.
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    retry_count = state.get("retry_count", 0)
    if issues:
        retry_count += 1

    return {
        "jd_text": response.text,
        "retry_count": retry_count,
    }


def policy_check_node(state: JDState) -> dict:
    jd_text = state.get("jd_text", "")
    normalized_text = " ".join(
        jd_text.casefold().replace("-", " ").split()
    )
    issues = []

    for phrase in BANNED_PHRASES:
        if phrase in normalized_text:
            issues.append(f"Remove inappropriate phrase: {phrase}")

    for requirement in state.get("requirements", []):
        requirement_text = requirement["text"].casefold()
        for phrase in PROTECTED_CHARACTERISTIC_PHRASES:
            if phrase in requirement_text:
                issues.append(
                    f"Remove protected-characteristic requirement: {phrase}"
                )

    for section_name, markers in REQUIRED_CONTENT.items():
        if not any(marker in normalized_text for marker in markers):
            issues.append(f"Add the required {section_name} content")

    return {"issues": issues}

def route_after_policy_check(state: JDState) -> str:
    if state.get("issues"):
        if state.get("retry_count", 0) < MAX_POLICY_RETRIES:
            return "draft_jd"
        return "policy_blocked"
    return "persist_draft"


def policy_blocked(state: JDState) -> dict:
    """Stop a draft from being published when automatic checks still find issues."""
    return {}


def extract_requirements(state: JDState) -> dict:
    prompt = f"""
Extract 5 to 10 distinct candidate requirements from this job description.
Use only these categories: skills, experience, qualification.
Mark each as required or preferred.
Assign a weight from 1 (lowest importance) to 5 (highest importance).
Return requirements grounded in the JD; do not invent qualifications.

Job description:
{state["jd_text"]}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RequirementsResponse,
        ),
    )

    parsed = RequirementsResponse.model_validate_json(response.text)
    return {"requirements": [item.model_dump() for item in parsed.requirements]}

def persist_draft(state: JDState) -> dict:
    with SessionLocal() as session:
        job = Job(
            title=state["role_title"],
            seniority=state["seniority"],
            status="approved",
            jd_text=state["jd_text"],
            created_by_id=state["created_by_id"],
            requirements=[
                JobRequirement(**requirement)
                for requirement in state["requirements"]
            ],
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        return {"job_id": job.id}

    
def build_jd_graph():
    graph = StateGraph(JDState)

    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("draft_jd", draft_jd)
    graph.add_node("extract_requirements", extract_requirements)
    graph.add_node("persist_draft", persist_draft)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("policy_blocked", policy_blocked)

    graph.add_edge(START, "retrieve_policy")
    graph.add_edge("retrieve_policy", "draft_jd")
    graph.add_edge("draft_jd", "extract_requirements")
    graph.add_edge("extract_requirements", "policy_check")
    graph.add_conditional_edges(
    "policy_check",
    route_after_policy_check,
    {
        "draft_jd": "draft_jd",
        "persist_draft": "persist_draft",
        "policy_blocked": "policy_blocked",
    },
    )
    graph.add_edge("persist_draft", END)
    graph.add_edge("policy_blocked", END)
    return graph.compile()

jd_graph = build_jd_graph()


if __name__ == "__main__":
    jd_graph = build_jd_graph()
