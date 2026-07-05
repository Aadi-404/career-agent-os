import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.history import JobOpportunityRecord, WorkspaceSummary, UserRecord
from app.main import app
from app.services.command_center_service import build_command_center
from tests.test_prep_memory_service import _analysis
from tests.test_opportunity_intelligence_service import _opportunity
from app.models.analysis import RequirementMatch
from app.models.system import ProductionReadinessResponse, ReadinessCheck


def _workspace(latest_analysis=None) -> WorkspaceSummary:
    return WorkspaceSummary(
        user=UserRecord(id="user-1", displayName="User", role="member", createdAt="2026-06-22T00:00:00Z"),
        resumeCount=1,
        jobDescriptionCount=1,
        analysisCount=1 if latest_analysis else 0,
        preparationSessionCount=0,
        jobOpportunityCount=1,
        latestAnalysis=latest_analysis,
    )


class CommandCenterServiceTests(unittest.TestCase):
    def test_command_center_prefers_score_when_no_analysis_exists(self):
        response = build_command_center(_workspace(), [], [], [])

        self.assertIn("No saved score", response.summary)
        self.assertEqual(response.topActions[0], "Run a score-only resume/JD match.")

    def test_command_center_combines_prep_and_pipeline_actions(self):
        weak_match = RequirementMatch(
            requirement="Azure cloud basics",
            category="cloud",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=20,
            matchType="missing",
            reason="No strong Azure proof.",
        )
        analysis = _analysis(weak_match)
        opportunity: JobOpportunityRecord = _opportunity("job-1", status="viewed", score=82)

        response = build_command_center(_workspace(analysis), [analysis], [], [opportunity])

        self.assertIn("actions ready", response.summary)
        self.assertTrue(any("Prepare Azure" in action for action in response.topActions))
        self.assertTrue(any("Shortlist" in action for action in response.topActions))
        self.assertEqual(response.opportunityActions.actions[0].recommendedStatus, "shortlisted")

    def test_command_center_surfaces_production_blockers(self):
        readiness = ProductionReadinessResponse(
            environment="production",
            readyForProduction=False,
            checks=[
                ReadinessCheck(key="auth", label="Auth", status="fail", detail="Auth is not enforced."),
                ReadinessCheck(key="cors", label="CORS", status="warn", detail="CORS uses a placeholder."),
            ],
            warnings=["Auth is not enforced.", "CORS uses a placeholder."],
        )

        response = build_command_center(_workspace(), [], [], [], readiness)

        self.assertIn("production blocker", response.summary)
        self.assertEqual(response.productionReadiness.readyForProduction, False)
        self.assertTrue(response.topActions[0].startswith("Resolve 1 production blocker"))

    def test_command_center_route_returns_aggregate_payload(self):
        weak_match = RequirementMatch(
            requirement="Azure cloud basics",
            category="cloud",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=20,
            matchType="missing",
            reason="No strong Azure proof.",
        )
        analysis = _analysis(weak_match)
        opportunity = _opportunity("job-1", status="viewed", score=82)
        workspace = _workspace(analysis)

        with (
            patch("app.main._authorize_user", return_value=None),
            patch("app.main.get_workspace_summary", return_value=workspace),
            patch("app.main.list_analyses", return_value=[analysis]),
            patch("app.main.list_preparation_sessions", return_value=[]),
            patch("app.main.list_job_opportunities_for_user", return_value=[opportunity]),
        ):
            response = TestClient(app).get("/ai/command-center/user-1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("actions ready", body["summary"])
        self.assertTrue(any("Shortlist" in item for item in body["topActions"]))


if __name__ == "__main__":
    unittest.main()
