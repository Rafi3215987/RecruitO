"""Focused regression checks for the Day 3 access and dashboard rules."""

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.main import app
from app.routers import applications as application_routes
from app.schemas.application import CandidateApplicationItem
from app.services.security import create_access_token


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeUserSession:
    def __init__(self, user):
        self.user = user

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def scalar(self, _statement):
        return self.user

    def expunge(self, _user):
        pass


class FakeJobSession(FakeUserSession):
    def __init__(self, job):
        self.job = job

    def scalar(self, _statement):
        return self.job

    def commit(self):
        pass

    def refresh(self, _job):
        pass

    def scalars(self, _statement):
        return FakeResult([self.job] if self.job.status == "approved" else [])


def make_user(user_id: int, role: str):
    return SimpleNamespace(id=user_id, role=role, is_active=True)


def make_job():
    return SimpleNamespace(
        id=81,
        title="Backend Engineer",
        seniority="Mid-level",
        status="draft",
        jd_text="Build and maintain backend services.",
        external_post_url=None,
        external_post_provider=None,
        blogger_post_id=None,
        contact_email=None,
        created_at=datetime.now(timezone.utc),
        created_by_id=7,
        requirements=[],
    )


class Day3PlanRulesTests(unittest.TestCase):
    def client_for(self, user):
        client = TestClient(app)
        client.cookies.set(
            "access_token",
            create_access_token(user.id, user.role),
        )
        return client

    def test_candidate_is_forbidden_from_job_management_routes(self):
        candidate = make_user(11, "candidate")
        payloads = [
            ("post", "/jobs/generate", {
                "role_title": "Backend Engineer",
                "seniority": "Mid-level",
                "key_skills": ["Python"],
                "employment_type": "full-time",
                "location_mode": "remote",
            }),
            ("post", "/jobs/assistant/chat", {
                "messages": [{"role": "user", "content": "Draft a backend job"}],
            }),
            ("put", "/jobs/81", {
                "jd_text": "Updated job description",
                "requirements": [],
                "external_post_url": None,
            }),
            ("post", "/jobs/81/approve", None),
            ("post", "/jobs/81/publish-blogger", None),
            ("post", "/jobs/81/rescore", {"reason": "Requirements were edited today"}),
            ("post", "/admin/applications/5/rescore", {"reason": "Requirements were edited today"}),
            ("post", "/jobs/81/applications/batch", None),
            ("get", "/jobs/81/ranking", None),
            ("get", "/applications/5/assessment", None),
        ]

        with patch(
            "app.dependencies.SessionLocal",
            side_effect=lambda: FakeUserSession(candidate),
        ):
            with self.client_for(candidate) as client:
                for method, path, payload in payloads:
                    with self.subTest(method=method, path=path):
                        response = getattr(client, method)(path, json=payload) if payload else getattr(client, method)(path)
                        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_withdraw_an_application_by_another_id(self):
        candidate = make_user(11, "candidate")
        captured_sql = {}

        class ScopedSession(FakeUserSession):
            def execute(self, statement):
                compiled = statement.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
                captured_sql["query"] = str(compiled)
                return FakeResult([])

        with (
            patch(
                "app.dependencies.SessionLocal",
                side_effect=lambda: FakeUserSession(candidate),
            ),
            patch(
                "app.routers.applications.SessionLocal",
                side_effect=lambda: ScopedSession(candidate),
            ),
        ):
            with self.client_for(candidate) as client:
                response = client.delete("/me/applications/902")
        # 404 rather than 403, so application ids cannot be probed.
        self.assertEqual(response.status_code, 404)
        self.assertIn("applications.candidate_id = 11", captured_sql["query"])

    def test_candidate_dashboard_filters_by_current_user_and_exposes_no_scores(self):
        candidate = make_user(11, "candidate")
        applied_at = datetime(2026, 10, 10, tzinfo=timezone.utc)
        rows = [
            (
                SimpleNamespace(
                    id=1,
                    candidate_id=11,
                    job_id=101,
                    status="submitted",
                    created_at=applied_at,
                    scheduling_status="not_queued",
                    scheduling_error_code=None,
                ),
                SimpleNamespace(id=101, title="Role for candidate A", seniority="Junior"),
                None,
            ),
            (
                SimpleNamespace(
                    id=2,
                    candidate_id=22,
                    job_id=202,
                    status="ranked",
                    created_at=applied_at,
                    scheduling_status="not_queued",
                    scheduling_error_code=None,
                ),
                SimpleNamespace(id=202, title="Private role for candidate B", seniority="Senior"),
                None,
            ),
        ]
        captured_sql = {}

        class CandidateSession(FakeUserSession):
            def execute(self, statement):
                compiled = statement.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
                captured_sql["query"] = str(compiled)
                return FakeResult([row for row in rows if row[0].candidate_id == candidate.id])

            def scalars(self, _statement):
                return FakeResult([])

        with (
            patch(
                "app.dependencies.SessionLocal",
                side_effect=lambda: FakeUserSession(candidate),
            ),
            patch(
                "app.routers.applications.SessionLocal",
                side_effect=lambda: CandidateSession(candidate),
            ),
        ):
            with self.client_for(candidate) as client:
                response = client.get("/me/applications")

        self.assertEqual(response.status_code, 200)
        self.assertIn("applications.candidate_id = 11", captured_sql["query"])
        body = response.json()
        self.assertEqual([item["job_title"] for item in body], ["Role for candidate A"])
        self.assertEqual(
            set(body[0]),
            {
                "id",
                "interview_id",
                "job_id",
                "job_title",
                "seniority",
                "applied_at",
                "status",
                "interview_scheduled_at",
                "interview_duration_minutes",
                "interview_scheduling_status",
                "interview_scheduling_error_code",
                "join_available",
            },
        )
        self.assertNotIn("score", response.text)
        self.assertNotIn("rank", response.text)
        self.assertEqual(body[0]["status"], "Under review")
        self.assertNotIn("Private role for candidate B", response.text)

    def test_manager_can_create_approve_and_publish_job_to_public_listing(self):
        manager = make_user(7, "hiring_manager")
        job = make_job()
        with (
            patch(
                "app.dependencies.SessionLocal",
                side_effect=lambda: FakeUserSession(manager),
            ),
            patch("app.main.SessionLocal", side_effect=lambda: FakeJobSession(job)),
            patch("app.main.jd_graph.invoke", return_value={"job_id": job.id}) as invoke,
            patch("app.main._auto_publish_job_to_blogger", AsyncMock(return_value=False)) as publish,
        ):
            with self.client_for(manager) as client:
                created = client.post(
                    "/jobs/generate",
                    json={
                        "role_title": job.title,
                        "seniority": job.seniority,
                        "key_skills": ["Python"],
                        "employment_type": "full-time",
                        "location_mode": "remote",
                    },
                )
                approved = client.post(f"/jobs/{job.id}/approve")
                approved_again = client.post(f"/jobs/{job.id}/approve")
                public_jobs = client.get("/public/jobs")

        # The JD graph persists a policy-checked job as approved and then tries Blogger.
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json(), {"job_id": job.id, "status": "approved"})
        invoke.assert_called_once()
        self.assertEqual(invoke.call_args.args[0]["created_by_id"], manager.id)
        publish.assert_awaited_once()
        # The approve route still accepts a draft and refuses a job that is already approved.
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "approved")
        self.assertEqual(approved_again.status_code, 409)
        self.assertEqual(public_jobs.status_code, 200)
        self.assertEqual([item["id"] for item in public_jobs.json()], [job.id])

    def test_candidate_statuses_match_day3_mapping(self):
        self.assertEqual(application_routes._candidate_status("submitted"), "Under review")
        self.assertEqual(application_routes._candidate_status("parsing"), "Under review")
        self.assertEqual(application_routes._candidate_status("screening"), "Under review")
        self.assertEqual(application_routes._candidate_status("ranked"), "Under review")
        self.assertEqual(application_routes._candidate_status("interview scheduled"), "Interview scheduled")
        self.assertEqual(application_routes._candidate_status("interview completed"), "Awaiting decision")

    def test_candidate_application_schema_has_no_private_assessment_fields(self):
        self.assertNotIn("score", CandidateApplicationItem.model_fields)
        self.assertNotIn("rank", CandidateApplicationItem.model_fields)
        self.assertNotIn("requirements", CandidateApplicationItem.model_fields)


if __name__ == "__main__":
    unittest.main()
