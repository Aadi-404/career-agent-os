import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.models.history import AcceptedResumeRewriteSaveRequest, ResumeVersionSaveRequest
from app.models.resume_normalize import StructuredResume
from app.services.history_store import (
    list_accepted_resume_rewrites,
    list_resume_versions,
    save_accepted_resume_rewrite,
    save_resume_version,
)


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
        self.version_inserted = None

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
        if "SELECT id FROM accepted_resume_rewrites" in query:
            return _Rows([{"id": "rewrite-1"}])
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
        if "INSERT INTO resume_versions" in query:
            self.version_inserted = {
                "id": params[0],
                "user_id": params[1],
                "resume_id": params[2],
                "analysis_id": params[3],
                "accepted_rewrite_id": params[4],
                "title": params[5],
                "change_summary": params[6],
                "normalized_text": params[7],
                "structured_json": params[8],
                "created_at": params[9],
            }
            return _Rows([])
        if "SELECT * FROM resume_versions WHERE id" in query:
            return _Rows([self.version_inserted])
        if "SELECT * FROM resume_versions WHERE user_id" in query:
            return _Rows([self.version_inserted])
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

    def test_save_and_list_resume_version(self):
        connection = _AcceptedRewriteConnection()
        structured = StructuredResume(
            profile={"name": "User 1", "summary": "Full stack engineer."},
            experience=[],
            projects=[{"name": "Data Tool", "techStack": ["Django"], "highlights": ["Built APIs."]}],
            skills=["Python", "Django"],
            education=[],
            achievements=[],
            certifications=[],
        )
        request = ResumeVersionSaveRequest(
            userId="user-1",
            resumeId="resume-1",
            analysisId="analysis-1",
            acceptedRewriteId="rewrite-1",
            title="Resume version after Django rewrite",
            changeSummary="Applied rewrite for Django API experience.",
            normalizedText="User 1\nProjects\nData Tool\n- Built APIs.",
            structuredResume=structured,
        )

        with patch("app.services.history_store.get_connection", lambda: _fake_connection(connection)):
            saved = save_resume_version(request)
            versions = list_resume_versions("user-1", resume_id="resume-1")

        self.assertEqual(saved.resumeId, "resume-1")
        self.assertEqual(saved.acceptedRewriteId, "rewrite-1")
        self.assertEqual(saved.structuredResume.projects[0].name, "Data Tool")
        self.assertEqual(versions[0].title, "Resume version after Django rewrite")


if __name__ == "__main__":
    unittest.main()
