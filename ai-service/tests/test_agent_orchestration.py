import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    CareerAgentPlanRequest,
    MissingSkill,
    PreparationIntelligence,
    ResearchContextNote,
    RequirementMatch,
    ScoreBreakdownItem,
    ShortlistingFactor,
    SystemDesignReadiness,
    WeaklyEvidencedSkill,
)
from app.services.agent_orchestration_service import build_career_agent_plan


def _request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText="Python Django React SQL Azure AI agent ETL project experience. " * 2,
        jobDescriptionText="Need Python AI Full Stack Engineer with ETL, agent guardrails, React, SQL, and Azure basics. " * 2,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "React", "SQL"],
            targetMarket="India product companies",
        ),
        preparationPlanDays=7,
    )


def _analysis() -> AnalysisResponse:
    matches = [
        RequirementMatch(
            requirement="AI agent guardrails",
            category="ai",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=15,
            matchType="missing",
            reason="Resume does not show guardrail implementation.",
        ),
        RequirementMatch(
            requirement="Django APIs",
            category="backend",
            importance="high",
            bestEvidence="Built Django APIs for data quality workflows.",
            evidenceSource="project",
            score=88,
            matchType="semantic+exact",
            reason="Direct project evidence.",
        ),
    ]
    return AnalysisResponse(
        technicalMatchScore=62,
        shortlistingScore=58,
        interviewReadinessScore=52,
        overallOpportunityScore=60,
        overallSummary="Partial fit with one AI-agent gap.",
        fitCategory="Partial Fit",
        scoreBreakdown=[ScoreBreakdownItem(category="projectEvidence", weight=20, score=60, weightedScore=12, reason="Some proof.")],
        shortlistingFactors=[ShortlistingFactor(factor="AI depth", impact="negative", reason="Guardrail proof is missing.")],
        requirementMatches=matches,
        recommendedAction="Prepare before applying.",
        matchingSkills=[],
        weaklyEvidencedSkills=[
            WeaklyEvidencedSkill(
                skill="AI agent guardrails",
                source="missing",
                whyWeak="No guardrail proof.",
                howToStrengthenResume="Add only truthful evidence or prepare this gap.",
            )
        ],
        missingSkills=[
            MissingSkill(
                skill="AI agent guardrails",
                importance="high",
                whyItMatters="Required for AI roles.",
                howToPrepare="Study permissions, rollback, validation, and evals.",
            )
        ],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Some backend depth.", topicsToPrepare=["Agent guardrails"]),
    )


class AgentOrchestrationTests(unittest.TestCase):
    def test_plan_prioritizes_preparation_for_high_importance_gap(self):
        plan = build_career_agent_plan(CareerAgentPlanRequest(sourceRequest=_request(), analysis=_analysis()))

        self.assertEqual(plan.phase, "Phase 8")
        self.assertIn("high-priority gaps", plan.headline)
        self.assertEqual(plan.recommendations[0].tool, "preparation_plan")
        self.assertEqual(plan.recommendations[0].priority, "critical")
        self.assertTrue(any(item.tool == "research_note" for item in plan.recommendations))
        self.assertTrue(any(item.tool == "resume_rewrite" and item.requiresPremium for item in plan.recommendations))
        self.assertTrue(any("Run score first" in guardrail for guardrail in plan.guardrails))

    def test_plan_marks_existing_research_and_preparation_as_satisfied(self):
        prep = PreparationIntelligence(summary="Prep exists", priorityTopics=[], dailyPlan=[], crossQuestionChains=[])
        note = ResearchContextNote(title="Demo research", summary="Company context reviewed.")
        plan = build_career_agent_plan(
            CareerAgentPlanRequest(
                sourceRequest=_request(),
                analysis=_analysis(),
                researchNotes=[note],
                preparation=prep,
                generatedArtifacts=["preparation_plan", "resume_rewrite"],
                company="DemoFin",
                roleTitle="Python AI Full Stack Engineer",
            )
        )

        satisfied = [item.tool for item in plan.recommendations if item.alreadySatisfied]
        self.assertIn("research_note", satisfied)
        self.assertIn("preparation_plan", satisfied)
        self.assertIn("resume_rewrite", satisfied)
        self.assertEqual(plan.recommendations[0].alreadySatisfied, False)
        self.assertTrue(any(signal == "Company context: DemoFin" for signal in plan.memorySignals))

    def test_agent_plan_route_records_usage_without_llm(self):
        client = TestClient(app)
        with (
            patch("app.main._enforce_ai_usage", return_value=None) as enforce_mock,
            patch("app.main._record_ai_usage", return_value=None) as record_mock,
        ):
            response = client.post(
                "/ai/agent/plan",
                json={
                    "sourceRequest": _request().model_dump(),
                    "analysis": _analysis().model_dump(),
                    "researchNotes": [],
                    "generatedArtifacts": [],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recommendations"][0]["tool"], "preparation_plan")
        enforce_mock.assert_called_once()
        record_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
