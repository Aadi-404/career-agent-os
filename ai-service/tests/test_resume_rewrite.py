import unittest

from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    RequirementMatch,
    ResumeRewriteRequest,
    ScoreBreakdownItem,
    SystemDesignReadiness,
)
from app.services.resume_rewrite_service import build_resume_rewrite


def _request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText="Built Django APIs for ETL validation and data quality reporting. " * 2,
        jobDescriptionText="Need Django APIs, ETL validation, AI agent guardrails, and cloud basics. " * 2,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "SQL"],
            targetMarket="India product companies",
        ),
    )


def _analysis() -> AnalysisResponse:
    return AnalysisResponse(
        technicalMatchScore=72,
        overallSummary="Rewrite test.",
        fitCategory="Good Fit",
        scoreBreakdown=[ScoreBreakdownItem(category="projectEvidence", weight=20, score=72, weightedScore=14.4, reason="test")],
        shortlistingFactors=[],
        requirementMatches=[
            RequirementMatch(
                requirement="Django APIs",
                category="backend",
                importance="high",
                bestEvidence="Built Django APIs for ETL validation and data quality reporting.",
                evidenceSource="project",
                score=86,
                matchType="exact",
                reason="Direct evidence.",
            ),
            RequirementMatch(
                requirement="AI agent guardrails",
                category="ai",
                importance="high",
                bestEvidence=None,
                evidenceSource="missing",
                score=10,
                matchType="missing",
                reason="Missing.",
            ),
        ],
        matchingSkills=[],
        weaklyEvidencedSkills=[],
        missingSkills=[],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="test", topicsToPrepare=[]),
    )


class ResumeRewriteTests(unittest.TestCase):
    def test_rewrite_marks_existing_evidence_as_safe(self):
        response = build_resume_rewrite(ResumeRewriteRequest(sourceRequest=_request(), analysis=_analysis(), resumeText=_request().resumeText))
        safe = next(item for item in response.suggestions if item.targetRequirement == "Django APIs")

        self.assertEqual(safe.proofSafety, "safe_from_existing_evidence")
        self.assertIn("Built Django APIs", safe.originalEvidence or "")

    def test_rewrite_marks_missing_requirement_as_gap(self):
        response = build_resume_rewrite(ResumeRewriteRequest(sourceRequest=_request(), analysis=_analysis(), resumeText=_request().resumeText))
        gap = next(item for item in response.suggestions if item.targetRequirement == "AI agent guardrails")

        self.assertEqual(gap.proofSafety, "gap_do_not_claim")
        self.assertIn("Do not claim", gap.rewrittenBullet)


if __name__ == "__main__":
    unittest.main()
