import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.services.history_store import get_workspace_summary


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _WorkspaceSummaryConnection:
    counts = {
        "resumes": 2,
        "job_descriptions": 3,
        "analyses": 4,
        "preparation_sessions": 5,
        "job_opportunities": 6,
        "research_notes": 7,
    }

    def execute(self, query, params=()):
        if "SELECT * FROM users" in query:
            return _Rows([{
                "id": "user-1",
                "display_name": "User 1",
                "email": "user@example.test",
                "role": "member",
                "subscription_tier": "free",
                "subscription_status": "inactive",
                "created_at": "2026-07-03T00:00:00Z",
            }])
        if "SELECT COUNT(*) AS count FROM" in query:
            table = query.split("FROM", 1)[1].split("WHERE", 1)[0].strip()
            return _Rows([{"count": self.counts[table]}])
        if "AVG(technical_match_score)" in query:
            return _Rows([{"average_score": 72, "best_score": 91}])
        if "FROM job_opportunities" in query and "active_count" in query:
            return _Rows([{
                "viewed_count": 1,
                "shortlisted_count": 1,
                "applied_count": 1,
                "active_count": 4,
                "interview_count": 1,
                "offer_count": 1,
                "rejected_count": 1,
                "archived_count": 0,
            }])
        if "FROM preparation_sessions" in query and "completed_count" in query:
            return _Rows([{"completed_count": 2}])
        if "SELECT * FROM analyses" in query:
            return _Rows([])
        return _Rows([])


@contextmanager
def _fake_connection(connection):
    yield connection


class WorkspaceSummaryTests(unittest.TestCase):
    def test_workspace_summary_includes_progress_analytics(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_WorkspaceSummaryConnection())):
            summary = get_workspace_summary("user-1")

        self.assertEqual(summary.resumeCount, 2)
        self.assertEqual(summary.researchNoteCount, 7)
        self.assertEqual(summary.averageMatchScore, 72)
        self.assertEqual(summary.bestMatchScore, 91)
        self.assertEqual(summary.activeOpportunityCount, 4)
        self.assertEqual(summary.interviewOpportunityCount, 1)
        self.assertEqual(summary.offerOpportunityCount, 1)
        self.assertEqual(summary.completedPreparationCount, 2)
        self.assertEqual(summary.pipelineStatusCounts["shortlisted"], 1)
        self.assertEqual(summary.pipelineStatusCounts["applied"], 1)
        self.assertEqual(summary.applicationToInterviewRate, 67)
        self.assertEqual(summary.interviewToOfferRate, 50)
        self.assertEqual(summary.positiveOutcomeRate, 67)


if __name__ == "__main__":
    unittest.main()
