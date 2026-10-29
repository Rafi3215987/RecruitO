import os
import logging
import json
import asyncio
from contextlib import suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg

from app.graphs.jobDescription_graph import jd_graph
from app.graphs.manager_job_chat_graph import manager_job_chat_graph

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from markdown_it import MarkdownIt

from app.db.session import SessionLocal
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.schemas.job import (
    JobGenerateRequest,
    JobGenerateResponse,
    JobResponse,
    JobUpdateRequest,
    JobListItem,
    PublicJobItem
)
from app.schemas.job_assistant import (
    JobAssistantChatRequest,
    JobAssistantChatResponse,
)
from app.routers.auth import (
    candidate_profile_router,
    interviewer_profile_router,
    staff_router,
    router as auth_router,
)
from app.routers.applications import (
    candidate_router as candidate_applications_router,
    manager_router as manager_applications_router,
    god_mode_router,
    god_mode_candidate_router,
    ranking_router,
    router as applications_router,
)
from app.routers.interviews import (
    interview_access_router,
    me_router as interviewer_interviews_router,
    router as interviews_router,
    god_mode_interviews_router,
)
from app.routers.chat import router as candidate_chat_router
from app.services.notifications import dispatch_pending_notifications
from app.services.screening_queue import dispatch_pending_screenings
from app.services.interview_analysis_queue import dispatch_pending_interview_analyses
from app.services.biometric_retention import delete_expired_biometric_enrollments
from app.services.interview_scheduling_queue import dispatch_pending_interview_scheduling
from app.services.interview_no_show_queue import dispatch_overdue_interview_no_shows

from fastapi import Depends
from app.dependencies import require_roles


app = FastAPI(title = "RecruitO API")


async def _auto_publish_job_to_blogger(job_id: int, actor) -> bool:
    if os.getenv("AUTO_PUBLISH_TO_BLOGGER", "true").strip().lower() != "true":
        return False
    try:
        await publish_job_to_blogger(job_id, actor)
        return True
    except HTTPException as exc:
        logger.warning(
            "Automatic Blogger publication skipped for job %s (HTTP %s)",
            job_id,
            exc.status_code,
        )
        return False


async def _notification_worker():
    last_biometric_cleanup = 0.0
    while True:
        try:
            await asyncio.to_thread(dispatch_overdue_interview_no_shows)
            await asyncio.to_thread(dispatch_pending_notifications)
            await asyncio.to_thread(dispatch_pending_screenings)
            await asyncio.to_thread(dispatch_pending_interview_analyses)
            await asyncio.to_thread(dispatch_pending_interview_scheduling)
            now = asyncio.get_running_loop().time()
            if now - last_biometric_cleanup >= 3600:
                await asyncio.to_thread(delete_expired_biometric_enrollments)
                last_biometric_cleanup = now
        except Exception:
            logger.exception("Notification outbox worker failed")
        await asyncio.sleep(20)


@app.on_event("startup")
async def start_notification_worker():
    if os.getenv("NOTIFICATION_WORKER_ENABLED", "false").lower() == "true":
        app.state.notification_worker = asyncio.create_task(_notification_worker())


@app.on_event("shutdown")
async def stop_notification_worker():
    worker = getattr(app.state, "notification_worker", None)
    if worker:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

app.include_router(auth_router)
app.include_router(candidate_profile_router)
app.include_router(interviewer_profile_router)
app.include_router(staff_router)
app.include_router(applications_router)
app.include_router(candidate_applications_router)
app.include_router(manager_applications_router)
app.include_router(god_mode_router)
app.include_router(god_mode_candidate_router)
app.include_router(ranking_router)
app.include_router(interviews_router)
app.include_router(god_mode_interviews_router)
app.include_router(interviewer_interviews_router)
app.include_router(interview_access_router)
app.include_router(candidate_chat_router)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Configure logging to inspect database errors on the server console
logging.basicConfig(level = logging.INFO)
logger = logging.getLogger("logs_RecruitO")

DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/health")
def health():
    db_status = "down"
    
    if DATABASE_URL:
        try:
            # Attempt to connect to Postgres
            conn = psycopg.connect(DATABASE_URL)
            with conn.cursor() as cur:  #send queries to the database
                cur.execute("SELECT 1;")
                cur.fetchone()
            conn.close()
            db_status = "up"
        except Exception as e:
            # Log the error internally without exposing details to the user
            logger.error(f"Database health check failed: {e}")

    return {
        "status": "ok",
        "db": db_status
    }

@app.post(
    "/jobs/generate",
    response_model=JobGenerateResponse,
    status_code=201,
)
async def generate_job(
    request: JobGenerateRequest,
    _current_user=Depends(require_roles("hiring_manager")),
):
    graph_input = request.model_dump()
    graph_input["created_by_id"] = _current_user.id
    result = await asyncio.to_thread(jd_graph.invoke, graph_input)
    if result.get("issues"):
        raise HTTPException(
            status_code=422,
            detail="The job description did not pass automated policy checks. Adjust the role details and try again.",
        )

    await _auto_publish_job_to_blogger(result["job_id"], _current_user)

    return JobGenerateResponse(
        job_id=result["job_id"],
        status="approved",
    )


@app.post(
    "/jobs/assistant/chat",
    response_model=JobAssistantChatResponse,
)
async def chat_with_job_assistant(
    request: JobAssistantChatRequest,
    current_user=Depends(require_roles("hiring_manager")),
):
    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=422,
            detail="The latest chat message must be from the hiring manager",
        )

    result = await asyncio.to_thread(
        manager_job_chat_graph.invoke,
        {
            "messages": [message.model_dump() for message in request.messages],
            "action": request.action,
            "created_by_id": current_user.id,
        },
    )
    if result.get("job_id"):
        await _auto_publish_job_to_blogger(result["job_id"], current_user)
    return JobAssistantChatResponse(
        assistant_message=result["assistant_message"],
        job_id=result.get("job_id"),
        status=result["status"],
    )


@app.get("/jobs", response_model=list[JobListItem])
def list_jobs(
    _current_user=Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        statement = select(Job).order_by(Job.created_at.desc())
        return session.scalars(statement).all()

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    _current_user=Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        statement = (
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )
        job = session.scalar(statement)

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        return job
@app.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, request: JobUpdateRequest,
               _current_user=Depends(require_roles("hiring_manager"))):
    with SessionLocal() as session:
        job = session.scalar(
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        old_external_url = job.external_post_url
        job.jd_text = request.jd_text
        job.external_post_url = request.external_post_url
        if job.external_post_provider == "blogger" and request.external_post_url != old_external_url:
            job.external_post_provider = None
            job.blogger_post_id = None
        job.requirements = [
            JobRequirement(**requirement.model_dump())
            for requirement in request.requirements
        ]

        session.commit()
        session.refresh(job)
        return job


@app.post("/jobs/{job_id}/publish-blogger", response_model=JobResponse)
async def publish_job_to_blogger(
    job_id: int,
    _current_user=Depends(require_roles("hiring_manager")),
):
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    mcp_url = os.getenv("BLOGGER_MCP_URL", "http://blogger-mcp:8001/mcp").strip()
    local_blogger_testing = os.getenv("ALLOW_LOCAL_BLOGGER_URL", "false").lower() == "true"
    is_local_http_url = public_base_url in (
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    )
    if not public_base_url.startswith("https://") and not (
        local_blogger_testing and is_local_http_url
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Set PUBLIC_BASE_URL to RecruitO's public HTTPS address before publishing to Blogger. "
                "For local draft testing only, set ALLOW_LOCAL_BLOGGER_URL=true and use "
                "http://localhost:5500 or http://127.0.0.1:5500."
            ),
        )

    with SessionLocal() as session:
        job = session.scalar(
            select(Job).options(selectinload(Job.requirements)).where(Job.id == job_id)
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "approved":
            raise HTTPException(status_code=409, detail="Approve the job before publishing it to Blogger")

        application_url = f"{public_base_url}/public-jobs.html?apply={job.id}"
        markdown = MarkdownIt("commonmark", {"html": False})
        content_html = markdown.render(job.jd_text)
        blogger_tool_url = mcp_url
        title = job.title
        seniority = job.seniority

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(blogger_tool_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as client:
                await client.initialize()
                result = await client.call_tool(
                    "publish_job",
                    {
                        "title": title,
                        "seniority": seniority,
                        "description_html": content_html,
                        "application_url": application_url,
                    },
                )
        # The MCP SDK exposes this flag as `isError`; older builds used `is_error`.
        if getattr(result, "isError", getattr(result, "is_error", False)):
            detail = "; ".join(getattr(block, "text", "Blogger MCP call failed") for block in result.content)
            raise RuntimeError(detail)
        response_data = json.loads(result.content[0].text)
    except Exception as exc:
        # Details stay in the server log; the client gets no internal error text (N12).
        logger.exception("Blogger publishing failed for job %s", job_id)
        raise HTTPException(
            status_code=502,
            detail="Blogger publishing failed. Check the Blogger and SMTP settings, then try again.",
        ) from exc

    with SessionLocal() as session:
        job = session.scalar(select(Job).options(selectinload(Job.requirements)).where(Job.id == job_id))
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        job.external_post_url = response_data["url"]
        job.external_post_provider = "blogger"
        job.blogger_post_id = response_data.get("post_id") or None
        session.commit()
        session.refresh(job)
        return job
    

@app.post("/jobs/{job_id}/approve", response_model=JobResponse)
def approve_job(
    job_id: int,
    _current_user=Depends(require_roles("hiring_manager"))):
    with SessionLocal() as session:
        job = session.scalar(
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != "draft":
            raise HTTPException(
                status_code=409,
                detail="Only draft jobs can be approved",
            )

        job.status = "approved"
        session.commit()
        session.refresh(job)
        return job
    
@app.get("/public/jobs", response_model=list[PublicJobItem])
def list_public_jobs():
    with SessionLocal() as session:
        statement = (
            select(Job)
            .where(Job.status == "approved")
            .order_by(Job.created_at.desc())
        )
        return session.scalars(statement).all()
