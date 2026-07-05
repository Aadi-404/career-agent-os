import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    MissingSkill,
    ResearchBuildRequest,
    ResearchContextNote,
    RequirementMatch,
    ScoreBreakdownItem,
    ShortlistingFactor,
    SystemDesignReadiness,
    WeaklyEvidencedSkill,
)
from app.services.preparation_service import build_preparation_intelligence
from app.services.research_enrichment_service import GoogleSearchItem
from app.services.research_service import build_research_note_draft


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
        preparationPlanDays=5,
        scoringCalibrationUserId="user-1",
    )


def _analysis() -> AnalysisResponse:
    matches = [
        RequirementMatch(
            requirement="AI agent guardrails",
            category="ai",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=25,
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
        technicalMatchScore=76,
        shortlistingScore=70,
        interviewReadinessScore=64,
        overallOpportunityScore=72,
        overallSummary="Good fit with one AI-agent guardrail gap.",
        fitCategory="Good Fit",
        scoreBreakdown=[ScoreBreakdownItem(category="projectEvidence", weight=20, score=70, weightedScore=14, reason="Good project proof.")],
        shortlistingFactors=[ShortlistingFactor(factor="Location", impact="neutral", reason="Remote is acceptable.")],
        requirementMatches=matches,
        recommendedAction="Apply after targeted prep.",
        matchingSkills=[],
        weaklyEvidencedSkills=[WeaklyEvidencedSkill(skill="AI agent guardrails", source="missing", whyWeak="No guardrail proof.", howToStrengthenResume="Prepare a truthful example.")],
        missingSkills=[MissingSkill(skill="AI agent guardrails", importance="high", whyItMatters="Important AI requirement.", howToPrepare="Study permissions and validation.")],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Some depth present.", topicsToPrepare=["AI agent guardrails"]),
    )


class ResearchGenerationTests(unittest.TestCase):
    def test_build_research_note_draft_uses_analysis_gaps_and_manual_context(self):
        draft = build_research_note_draft(
            ResearchBuildRequest(
                sourceRequest=_request(),
                analysis=_analysis(),
                company="DemoFin",
                roleTitle="Python AI Full Stack Engineer",
                researchType="interview",
                manualContext="Expect questions on tool permissions\nExpect ETL reliability follow-ups",
                sourceUrls=["https://example.com/interview"],
            )
        )

        self.assertEqual(draft.company, "DemoFin")
        self.assertEqual(draft.researchType, "interview")
        self.assertIn("AI agent guardrails", draft.preparationTopics)
        self.assertTrue(any("tool permissions" in signal for signal in draft.keySignals))
        self.assertEqual(draft.sources[1].url, "https://example.com/interview")
        self.assertEqual(draft.sources[1].citationQuality, "verified_url")
        self.assertEqual(draft.sources[1].sourceType, "interview_experience")

    def test_research_source_quality_flags_weak_citations(self):
        draft = build_research_note_draft(
            ResearchBuildRequest(
                sourceRequest=_request(),
                analysis=_analysis(),
                manualContext="Company blog says AI safety is important.",
                sourceUrls=["not-a-url"],
            )
        )

        weak_source = draft.sources[1]
        self.assertEqual(weak_source.citationQuality, "weak")
        self.assertTrue(any("valid http" in issue for issue in weak_source.validationIssues))

    def test_research_enrichment_adds_query_plan_sources(self):
        draft = build_research_note_draft(
            ResearchBuildRequest(
                sourceRequest=_request(),
                analysis=_analysis(),
                company="DemoFin",
                roleTitle="Python AI Full Stack Engineer",
                researchType="company",
            )
        )

        self.assertTrue(any("Research provider local prepared" in signal for signal in draft.keySignals))
        self.assertTrue(any("Company research:" in signal for signal in draft.keySignals))
        self.assertTrue(any("Interview research:" in signal for signal in draft.keySignals))
        self.assertTrue(any("Market research:" in signal for signal in draft.keySignals))
        self.assertIn("Research enrichment separated", draft.summary)
        self.assertTrue(any(source.title.startswith("Planned search:") for source in draft.sources))
        self.assertTrue(any(source.citationQuality == "weak" for source in draft.sources if source.title.startswith("Planned search:")))

    def test_google_research_provider_adds_cited_sources_without_heavy_llm_call(self):
        with (
            patch(
                "app.services.research_enrichment_service.get_settings",
                return_value=SimpleNamespace(
                    research_provider="google",
                    google_api_key="test-key",
                    google_search_engine_id="test-cx",
                ),
            ),
            patch(
                "app.services.research_enrichment_service.GoogleResearchEnrichmentProvider._search",
                return_value=[
                    GoogleSearchItem(
                        title="DemoFin Python AI Full Stack interview experience",
                        url="https://example.com/demofin-interview",
                        snippet="Recent interview notes mention Django APIs and AI guardrail design.",
                    )
                ],
            ) as search_mock,
        ):
            draft = build_research_note_draft(
                ResearchBuildRequest(
                    sourceRequest=_request(),
                    analysis=_analysis(),
                    company="DemoFin",
                    roleTitle="Python AI Full Stack Engineer",
                    researchType="interview",
                )
            )

        self.assertGreaterEqual(search_mock.call_count, 1)
        self.assertTrue(any("Google research provider returned" in signal for signal in draft.keySignals))
        self.assertTrue(any(source.url == "https://example.com/demofin-interview" for source in draft.sources))
        cited_source = next(source for source in draft.sources if source.url == "https://example.com/demofin-interview")
        self.assertEqual(cited_source.citationQuality, "verified_url")
        self.assertEqual(cited_source.sourceType, "company_page")

    def test_preparation_uses_saved_research_notes(self):
        prep = build_preparation_intelligence(
            _request(),
            _analysis().requirementMatches,
            _analysis().scoreBreakdown,
            research_notes=[
                ResearchContextNote(
                    title="DemoFin interview note",
                    company="DemoFin",
                    roleTitle="Python AI Full Stack Engineer",
                    researchType="interview",
                    summary="Recent notes emphasize agent permissions.",
                    keySignals=["Expect cross-questions on agent rollback"],
                    preparationTopics=["Agent tool permission design"],
                )
            ],
        )

        self.assertIn("research memory", prep.summary)
        self.assertEqual(prep.priorityTopics[0].topic, "Agent tool permission design")
        self.assertTrue(any("cited web sources" in item for item in prep.phase5ResearchBacklog))


if __name__ == "__main__":
    unittest.main()
