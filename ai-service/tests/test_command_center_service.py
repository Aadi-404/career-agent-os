import unittest

from app.models.history import JobOpportunityRecord, WorkspaceSummary, UserRecord
from app.services.command_center_service import build_command_center
from tests.test_prep_memory_service import _analysis
from tests.test_opportunity_intelligence_service import _opportunity
from app.models.analysis import RequirementMatch


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


if __name__ == "__main__":
    unittest.main()
