import unittest

from app.models.analysis import (
    AnalysisResponse,
    ApplicationDecisionRequest,
    AnalyzeRequest,
    CandidateContext,
    ResearchContextNote,
    RequirementMatch,
    ScoreBreakdownItem,
    SystemDesignReadiness,
)
from app.services.application_decision_service import build_application_decision


def _request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText="Python Django React SQL Azure ETL AI agent project evidence. " * 2,
        jobDescriptionText="Python AI Full Stack role needing Django, React, SQL, ETL, Azure, and agent guardrails. " * 2,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "React", "SQL"],
            targetMarket="India product companies",
        ),
    )


def _analysis(score: int, high_gap_score: int) -> AnalysisResponse:
    return AnalysisResponse(
        technicalMatchScore=score,
        shortlistingScore=score - 4,
        interviewReadinessScore=score - 8,
        overallOpportunityScore=score - 2,
        overallSummary="Decision test analysis.",
        fitCategory="Strong Fit" if score >= 80 else "Partial Fit",
        scoreBreakdown=[ScoreBreakdownItem(category="coreSkills", weight=25, score=score, weightedScore=20, reason="test")],
        shortlistingFactors=[],
        requirementMatches=[
            RequirementMatch(
                requirement="AI agent guardrails",
                category="ai",
                importance="high",
                bestEvidence="Agent workflow project" if high_gap_score >= 65 else None,
                evidenceSource="project" if high_gap_score >= 65 else "missing",
                score=high_gap_score,
                matchType="semantic" if high_gap_score >= 65 else "missing",
                reason="test",
            )
        ],
        matchingSkills=[],
        weaklyEvidencedSkills=[],
        missingSkills=[],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="test", topicsToPrepare=[]),
    )


class ApplicationDecisionTests(unittest.TestCase):
    def test_strong_score_with_research_applies_now(self):
        response = build_application_decision(
            ApplicationDecisionRequest(
                sourceRequest=_request(),
                analysis=_analysis(84, 78),
                company="DemoFin",
                researchNotes=[
                    ResearchContextNote(
                        title="DemoFin note",
                        summary="Company expects practical agent safety examples.",
                        keySignals=["Agent safety questions are common"],
                        preparationTopics=["Agent guardrails"],
                    )
                ],
            )
        )

        self.assertEqual(response.decision, "apply")
        self.assertEqual(response.confidence, "medium")
        self.assertTrue(response.researchSignalsUsed)
        self.assertTrue(any(step.actionType == "apply" and step.status == "ready" for step in response.executionPlan))
        self.assertTrue(any(step.id == "track-opportunity" for step in response.executionPlan))

    def test_gap_heavy_score_prepares_first(self):
        response = build_application_decision(
            ApplicationDecisionRequest(
                sourceRequest=_request(),
                analysis=_analysis(62, 20),
                company="DemoFin",
            )
        )

        self.assertEqual(response.decision, "prepare_first")
        self.assertTrue(any("AI agent guardrails" in blocker for blocker in response.blockers))
        self.assertIn("No company or role research note is attached yet.", response.blockers)
        self.assertEqual(response.executionPlan[0].id, "research-note")
        self.assertTrue(any(step.id == "preparation-plan" and step.priority == "critical" for step in response.executionPlan))
        review_step = next(step for step in response.executionPlan if step.id == "review-after-prep")
        self.assertEqual(review_step.status, "blocked")
        self.assertIn("preparation-plan", review_step.dependsOn)


if __name__ == "__main__":
    unittest.main()
