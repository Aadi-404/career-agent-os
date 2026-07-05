import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.models.history import AcceptedResumeRewriteSaveRequest
from app.services.history_store import list_accepted_resume_rewrites, save_accepted_resume_rewrite


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _AcceptedRewriteConnection:
    def __init__(self):
        self.inserted = None

    def execute(self, query, params=()):
        if "SELECT * FROM users" in query:
            return _Rows([{
                "id": "user-1",
                "display_name": "User 1",
                "email": "user@example.test",
                "role": "member",
                "subscription_tier": "premium",
                "subscription_status": "active",
                "created_at": "2026-07-05T00:00:00Z",
            }])
        if "SELECT id FROM analyses" in query:
            return _Rows([{"id": "analysis-1"}])
        if "SELECT id FROM resumes" in query:
            return _Rows([{"id": "resume-1"}])
        if "SELECT id FROM job_descriptions" in query:
            return _Rows([{"id": "jd-1"}])
        if "INSERT INTO accepted_resume_rewrites" in query:
            self.inserted = {
                "id": params[0],
                "user_id": params[1],
                "analysis_id": params[2],
                "resume_id": params[3],
                "job_description_id": params[4],
                "target_requirement": params[5],
                "evidence_source": params[6],
                "proof_safety": params[7],
                "original_evidence": params[8],
                "current_issue": params[9],
                "accepted_bullet": params[10],
                "reason": params[11],
                "target_section": params[12],
                "target_label": params[13],
                "created_at": params[14],
            }
            return _Rows([])
        if "SELECT * FROM accepted_resume_rewrites WHERE id" in query:
            return _Rows([self.inserted])
        if "SELECT * FROM accepted_resume_rewrites WHERE user_id" in query:
            return _Rows([self.inserted])
        return _Rows([])


@contextmanager
def _fake_connection(connection):
    yield connection


class AcceptedResumeRewriteTests(unittest.TestCase):
    def test_save_and_list_accepted_rewrite(self):
        connection = _AcceptedRewriteConnection()
        request = AcceptedResumeRewriteSaveRequest(
            userId="user-1",
            analysisId="analysis-1",
            resumeId="resume-1",
            jobDescriptionId="jd-1",
            targetRequirement="Django API experience",
            evidenceSource="project",
            proofSafety="safe_from_existing_evidence",
            originalEvidence="Built Django APIs for ETL validation.",
            currentIssue="Evidence exists but lacks measurable impact.",
            acceptedBullet="Built Django APIs for ETL validation, reducing manual checks by 40%.",
            reason="Uses existing project proof with quantified wording.",
            targetSection="project",
            targetLabel="Data Simplified Tool",
        )

        with patch("app.services.history_store.get_connection", lambda: _fake_connection(connection)):
            saved = save_accepted_resume_rewrite(request)
            records = list_accepted_resume_rewrites("user-1")

        self.assertEqual(saved.targetRequirement, "Django API experience")
        self.assertEqual(saved.proofSafety, "safe_from_existing_evidence")
        self.assertEqual(saved.targetSection, "project")
        self.assertEqual(saved.targetLabel, "Data Simplified Tool")
        self.assertEqual(records[0].acceptedBullet, saved.acceptedBullet)


if __name__ == "__main__":
    unittest.main()
