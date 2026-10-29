"""Offline unit tests for CV text extraction and the deterministic score calculator."""

import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from app.services.screening import evaluate_resume, extract_resume_text


class ScreeningTests(unittest.TestCase):
    def test_extracts_docx_paragraph_text(self):
        content = BytesIO()
        with ZipFile(content, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Python backend engineer with several years experience building APIs and databases.</w:t></w:r></w:p></w:body></w:document>',
            )
        text = extract_resume_text(content.getvalue(), "resume.docx")
        self.assertIn("Python backend engineer", text)

    def test_computes_weighted_score_and_checks_quotes(self):
        requirements = [
            {"text": "Python", "kind": "required", "category": "skills", "weight": 4},
            {"text": "Database experience", "kind": "preferred", "category": "experience", "weight": 2},
        ]
        model_text = json.dumps({"evaluations": [
            {"requirement_index": 0, "status": "met", "evidence_quote": "Python APIs", "rationale": "Direct evidence."},
            {"requirement_index": 1, "status": "partially_met", "evidence_quote": "PostgreSQL", "rationale": "Related database evidence."},
        ]})
        class FakeModels:
            def generate_content(self, **_kwargs):
                return type("Response", (), {"text": model_text})()
        class FakeClient:
            def __init__(self, **_kwargs):
                self.models = FakeModels()
            def __enter__(self): return self
            def __exit__(self, *_args): return False
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unit-test-key"}), patch("app.services.screening.genai.Client", FakeClient):
            result = evaluate_resume("Python APIs and PostgreSQL experience.", requirements, "test-model")
        self.assertEqual(result["total_score"], 83.33)
        self.assertEqual(len(result["justifications"]), 2)

    def test_rejects_unverifiable_evidence(self):
        requirements = [{"text": "Python", "kind": "required", "category": "skills", "weight": 4}]
        model_text = json.dumps({"evaluations": [
            {"requirement_index": 0, "status": "met", "evidence_quote": "invented quote", "rationale": "claim"},
        ]})
        class FakeModels:
            def generate_content(self, **_kwargs):
                return type("Response", (), {"text": model_text})()
        class FakeClient:
            def __init__(self, **_kwargs):
                self.models = FakeModels()
            def __enter__(self): return self
            def __exit__(self, *_args): return False
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unit-test-key"}), patch("app.services.screening.genai.Client", FakeClient):
            with self.assertRaisesRegex(ValueError, "could not be verified"):
                evaluate_resume("No matching language in this CV at all.", requirements, "test-model")


if __name__ == "__main__":
    unittest.main()
