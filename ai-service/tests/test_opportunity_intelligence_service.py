import unittest

from app.models.history import JobOpportunityRecord
from app.services.opportunity_intelligence_service import build_opportunity_next_actions


def _opportunity(
    record_id: str,
    *,
    status: str = "viewed",
    score: int | None = 75,
    optional_artifacts: dict | None = None,
) -> JobOpportunityRecord:
    return JobOpportunityRecord(
        id=record_id,
        userId="user-1",
        title=f"Role {record_id}",
        company="DemoCo",
        location="Remote",
        description="A detailed job description for a full stack AI developer role.",
        status=status,
        technicalMatchScore=score,
        fitCategory="Good Fit" if score and score >= 70 else "Partial Fit",
        optionalArtifacts=optional_artifacts or {},
        createdAt="2026-06-22T00:00:00Z",
        updatedAt="2026-06-22T00:00:00Z",
    )


class OpportunityIntelligenceServiceTests(unittest.TestCase):
    def test_high_score_viewed_role_should_be_shortlisted(self):
        response = build_opportunity_next_actions([_opportunity("job-1", status="viewed", score=82)])

        self.assertEqual(response.actions[0].recommendedStatus, "shortlisted")
        self.assertEqual(response.actions[0].priority, "high")
        self.assertIn("Shortlist", response.actions[0].action)

    def test_shortlisted_role_recommends_missing_artifacts_before_apply(self):
        response = build_opportunity_next_actions([_opportunity("job-2", status="shortlisted", score=76)])

        self.assertEqual(response.actions[0].artifactKey, "resume_improvements")
        self.assertEqual(response.actions[0].endpoint, "/ai/resume-improvements")

        response_with_resume = build_opportunity_next_actions([
            _opportunity("job-2", status="shortlisted", score=76, optional_artifacts={"resume_improvements": {"generatedAt": "now"}})
        ])

        self.assertEqual(response_with_resume.actions[0].artifactKey, "interview_questions")

    def test_low_score_viewed_role_can_be_archived(self):
        response = build_opportunity_next_actions([_opportunity("job-3", status="viewed", score=34)])

        self.assertEqual(response.actions[0].recommendedStatus, "archived")
        self.assertIn("below", response.actions[0].reason)


if __name__ == "__main__":
    unittest.main()
