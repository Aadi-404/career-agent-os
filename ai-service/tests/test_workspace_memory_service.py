import unittest

from app.models.analysis import AnalysisResponse, AnalyzeRequest, CandidateContext, DebugInfo, RequirementMatch, SystemDesignReadiness
from app.models.history import AnalysisRecord, ResearchNoteRecord
from app.services.workspace_memory_service import build_workspace_memory


def _request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText="Python Django React SQL Azure AI agent project evidence. " * 2,
        jobDescriptionText="Need Python AI Full Stack Engineer with Django, React, SQL, Azure, and agent guardrails. " * 2,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "React"],
            targetMarket="India product companies",
        ),
    )


def _analysis() -> AnalysisRecord:
    response = AnalysisResponse(
        technicalMatchScore=72,
        overallSummary="Good fit with one agent guardrail gap.",
        fitCategory="Good Fit",
        matchingSkills=[],
        weaklyEvidencedSkills=[],
        missingSkills=[],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Some gaps.", topicsToPrepare=[]),
        requirementMatches=[
            RequirementMatch(
                requirement="Django APIs",
                category="backend",
                importance="high",
                bestEvidence="Built Django APIs for data validation.",
                evidenceSource="project",
                score=86,
                matchType="semantic",
                reason="Strong evidence.",
            ),
            RequirementMatch(
                requirement="AI agent guardrails",
                category="ai",
                importance="high",
                bestEvidence=None,
                evidenceSource="missing",
                score=25,
                matchType="missing",
                reason="No guardrail proof.",
            ),
        ],
        debug=DebugInfo(mode="mock", promptPreview="", receivedExperienceYears=3, receivedTargetRole="Python AI Full Stack Engineer", receivedCurrentStack=["Python"], scoreReason="test"),
    )
    return AnalysisRecord(
        id="analysis-1",
        userId="user-1",
        title="Python AI role",
        technicalMatchScore=72,
        fitCategory="Good Fit",
        request=_request(),
        response=response,
        createdAt="2026-07-07T00:00:00Z",
    )


class WorkspaceMemoryServiceTests(unittest.TestCase):
    def test_workspace_memory_builds_retrieval_context_from_saved_items(self):
        memory = build_workspace_memory(
            user_id="user-1",
            resumes=[],
            job_descriptions=[],
            analyses=[_analysis()],
            research_notes=[
                ResearchNoteRecord(
                    id="research-1",
                    userId="user-1",
                    title="DemoFin research",
                    company="DemoFin",
                    roleTitle="Python AI Full Stack Engineer",
                    researchType="interview",
                    summary="Interview notes emphasize agent safety.",
                    keySignals=["Agent guardrail cross-questions"],
                    preparationTopics=["AI agent guardrails"],
                    sources=[],
                    createdAt="2026-07-07T00:00:00Z",
                    updatedAt="2026-07-07T00:00:00Z",
                )
            ],
            preparation_sessions=[],
            opportunities=[],
        )

        self.assertEqual(memory.userId, "user-1")
        self.assertGreater(memory.memoryScore, 0)
        self.assertTrue(any(item.sourceType == "analysis" for item in memory.topEvidence))
        self.assertEqual(memory.recurringGaps[0].topic, "AI agent guardrails")
        self.assertTrue(any("AI agent guardrails" in query for query in memory.retrievalQueries))


if __name__ == "__main__":
    unittest.main()
