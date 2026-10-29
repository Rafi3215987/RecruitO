"""Offline tests for batch CV import, the in-graph scoring retry, and imported-candidate safeguards."""

from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.graphs import cv_screening_graph as graph_module
from app.main import app
from app.services import cv_import
from app.services.cv_import import ResumeUploadError, validate_resume_upload
from app.services.notifications import queue_email
from app.services.security import create_access_token


def docx_bytes() -> bytes:
    content = BytesIO()
    with ZipFile(content, "w") as archive:
        archive.writestr("word/document.xml", "<w:document xmlns:w='urn:w'/>")
    return content.getvalue()


class ResumeValidationTests(unittest.TestCase):
    def test_accepts_pdf_and_docx_signatures(self):
        self.assertEqual(validate_resume_upload("cv.pdf", b"%PDF-1.7 body"), ("cv.pdf", ".pdf"))
        self.assertEqual(validate_resume_upload("dir/cv.DOCX", docx_bytes()), ("cv.DOCX", ".docx"))

    def test_rejects_wrong_type_spoofed_content_and_oversize(self):
        with self.assertRaises(ResumeUploadError) as wrong_type:
            validate_resume_upload("cv.txt", b"plain text")
        self.assertEqual(wrong_type.exception.status_code, 422)
        with self.assertRaises(ResumeUploadError) as spoofed:
            validate_resume_upload("cv.pdf", b"not really a pdf")
        self.assertEqual(spoofed.exception.status_code, 422)
        with self.assertRaises(ResumeUploadError) as oversize:
            validate_resume_upload("cv.pdf", b"%PDF-" + b"0" * cv_import.MAX_RESUME_BYTES)
        self.assertEqual(oversize.exception.status_code, 413)

    def test_rejected_file_does_not_touch_the_database(self):
        with patch("app.services.cv_import.SessionLocal") as session_factory:
            result = cv_import.import_resume_file(4, "notes.txt", b"hello", actor_user_id=7)
        self.assertEqual(result["status"], "rejected")
        session_factory.assert_not_called()

    def test_display_name_comes_from_the_file_name(self):
        self.assertEqual(cv_import._display_name("cv_03-jane.doe.pdf"), "Cv 03 Jane Doe")
        self.assertEqual(cv_import._display_name("___.pdf"), "Imported candidate")


class ImportedCandidateSafeguardTests(unittest.TestCase):
    def test_reserved_invalid_addresses_are_never_queued(self):
        session = MagicMock()
        queue_email(session, application_id=1, recipient=f"abc@{cv_import.IMPORTED_EMAIL_DOMAIN}",
                    status_key="candidate-status:submitted", subject="s", body="b")
        session.add.assert_not_called()
        session.scalar.assert_not_called()

    def test_imported_email_detection(self):
        self.assertTrue(cv_import.is_imported_candidate_email(f"x@{cv_import.IMPORTED_EMAIL_DOMAIN}"))
        self.assertFalse(cv_import.is_imported_candidate_email("person@example.com"))


class ScreeningGraphRetryTests(unittest.TestCase):
    def state(self):
        return {"score_id": 1, "resume_text": "text", "requirements": [], "model_name": "m", "job_description": ""}

    def test_invalid_output_retries_then_rejects(self):
        state = self.state()
        with patch.object(graph_module, "evaluate_resume", side_effect=ValueError("bad quote")):
            for expected_attempts in range(1, graph_module.MAX_EVALUATION_ATTEMPTS + 1):
                state.update(graph_module.evaluate_cv(state))
                self.assertEqual(state["evaluation_attempts"], expected_attempts)
                expected_route = ("reject_evaluation" if expected_attempts == graph_module.MAX_EVALUATION_ATTEMPTS
                                  else "evaluate_cv")
                self.assertEqual(graph_module.route_evaluation(state), expected_route)
        with self.assertRaises(graph_module.ScreeningInputError) as rejected:
            graph_module.reject_evaluation(state)
        self.assertEqual(rejected.exception.code, "SCORING_OUTPUT_INVALID")

    def test_valid_output_after_a_retry_is_persisted(self):
        state = self.state()
        with patch.object(graph_module, "evaluate_resume", side_effect=[ValueError("bad"), {"total_score": 50.0}]):
            state.update(graph_module.evaluate_cv(state))
            self.assertEqual(graph_module.route_evaluation(state), "evaluate_cv")
            state.update(graph_module.evaluate_cv(state))
        self.assertEqual(graph_module.route_evaluation(state), "persist_cv_assessment")
        self.assertEqual(state["result"], {"total_score": 50.0})

    def test_graph_has_retry_and_rejection_paths(self):
        nodes = set(graph_module.cv_screening_graph.get_graph().nodes)
        self.assertTrue({"evaluate_cv", "persist_cv_assessment", "reject_evaluation"} <= nodes)


class BatchImportRouteTests(unittest.TestCase):
    def client_for(self, user):
        client = TestClient(app)
        client.cookies.set("access_token", create_access_token(user.id, user.role))
        return client

    def run_batch(self, job_status: str, files):
        manager = SimpleNamespace(id=7, role="hiring_manager", is_active=True)
        auth_session = MagicMock()
        auth_session.__enter__.return_value.scalar.return_value = manager
        job_session = MagicMock()
        job_session.__enter__.return_value.get.return_value = SimpleNamespace(id=4, status=job_status)
        imported = []

        def fake_import(job_id, file_name, content, actor_user_id):
            imported.append((job_id, file_name, actor_user_id))
            return {"file_name": file_name, "status": "queued" if file_name.endswith(".pdf") else "rejected"}

        with (
            patch("app.dependencies.SessionLocal", return_value=auth_session),
            patch("app.routers.applications.SessionLocal", return_value=job_session),
            patch("app.routers.applications.import_resume_file", side_effect=fake_import),
        ):
            with self.client_for(manager) as client:
                response = client.post("/jobs/4/applications/batch", files=files)
        return response, imported

    def test_each_file_is_imported_independently(self):
        response, imported = self.run_batch("approved", [
            ("resume_files", ("a.pdf", b"%PDF-1", "application/pdf")),
            ("resume_files", ("b.txt", b"text", "text/plain")),
        ])
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual((body["queued"], body["rejected"]), (1, 1))
        self.assertEqual(imported, [(4, "a.pdf", 7), (4, "b.txt", 7)])

    def test_unapproved_job_is_refused(self):
        response, imported = self.run_batch("draft", [("resume_files", ("a.pdf", b"%PDF-1", "application/pdf"))])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(imported, [])


if __name__ == "__main__":
    unittest.main()
