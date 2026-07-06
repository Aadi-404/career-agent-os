import unittest
from datetime import datetime, timezone

from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    DebugInfo,
    RequirementMatch,
    SystemDesignReadiness,
)
from app.models.history import AnalysisRecord, PreparationSessionRecord
from app.models.prep_memory import PrepMemoryResponse
from app.services.prep_memory_service import build_prep_memory


def _analysis(match: RequirementMatch) -> AnalysisRecord:
    request = AnalyzeRequest(
        resumeText="Experienced full stack developer with Python, React, SQL, Azure, and API project delivery experience.",
        jobDescriptionText="Looking for a full stack developer with Azure, Python, SQL, React, APIs, and cloud fundamentals.",
        candidateContext=CandidateContext(
            targetRole="Full Stack Developer",
            experienceYears=3,
            currentStack=["Python", "React", "SQL"],
            targetMarket="Indian software job market",
        ),
    )
    response = AnalysisResponse(
        technicalMatchScore=50,
        overallSummary="Partial fit.",
        fitCategory="Partial Fit",
        matchingSkills=[],
        weaklyEvidencedSkills=[],
        missingSkills=[],
        resumeImprovements=[],
        interviewQuestions=[],
        crossQuestions=[],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Some gaps.", topicsToPrepare=[]),
        requirementMatches=[match],
        debug=DebugInfo(
            mode="mock",
            promptPreview="",
            receivedExperienceYears=3,
            receivedTargetRole="Full Stack Developer",
            receivedCurrentStack=["Python", "React", "SQL"],
            scoreReason="test",
        ),
    )
    return AnalysisRecord(
        id="analysis-1",
        userId="user-1",
        title="Analysis",
        technicalMatchScore=50,
        fitCategory="Partial Fit",
        request=request,
        response=response,
        createdAt="2026-06-22T00:00:00Z",
    )


class PrepMemoryServiceTests(unittest.TestCase):
    def test_build_prep_memory_detects_repeated_weak_and_unfinished_progress(self):
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
        session = PreparationSessionRecord(
            id="prep-1",
            userId="user-1",
            title="Azure prep",
            status="in_progress",
            plan={
                "dailyPlan": [
                    {
                        "day": 1,
                        "focus": "Azure",
                        "goal": "Strengthen cloud basics.",
                        "tasks": ["Review Azure services", "Practice AZ-900 scenario questions"],
                        "output": "Notes",
                    }
                ]
            },
            progress={
                "tasks": {"day-1-task-0": "done", "day-1-task-1": "todo"},
                "confidence": {"day-1": "low"},
            },
            createdAt="2026-06-22T00:00:00Z",
            updatedAt="2026-06-22T00:00:00Z",
        )

        memory = build_prep_memory([_analysis(weak_match)], [session])

        self.assertIsInstance(memory, PrepMemoryResponse)
        self.assertEqual(memory.repeatedWeakTopics[0].topic, "Azure cloud basics")
        self.assertEqual(memory.unfinishedPreparation[0].unfinishedTaskCount, 1)
        self.assertIsNotNone(memory.nextAction)
        self.assertEqual(memory.nextAction.kind, "track_today_focus")
        self.assertEqual(memory.nextAction.sessionId, "prep-1")
        self.assertEqual(memory.nextAction.taskId, "day-1-task-1")
        self.assertTrue(memory.nextRecommendedActions)

    def test_build_prep_memory_counts_plan_tasks_when_progress_is_empty(self):
        weak_match = RequirementMatch(
            requirement="React performance optimization",
            category="frontend",
            importance="medium",
            bestEvidence=None,
            evidenceSource="missing",
            score=45,
            matchType="weak",
            reason="Only basic React evidence.",
        )
        session = PreparationSessionRecord(
            id="prep-2",
            userId="user-1",
            title="Frontend prep",
            status="planned",
            plan={
                "summary": "Prepare frontend topics.",
                "priorityTopics": [],
                "dailyPlan": [
                    {
                        "day": 1,
                        "focus": "React",
                        "goal": "Build depth.",
                        "tasks": ["Review memoization", "Practice profiling"],
                        "output": "Notes",
                    }
                ],
                "crossQuestionChains": [],
                "phase5ResearchBacklog": [],
            },
            progress={},
            createdAt="2026-06-22T00:00:00Z",
            updatedAt="2026-06-22T00:00:00Z",
        )

        memory = build_prep_memory([_analysis(weak_match)], [session])

        self.assertEqual(memory.unfinishedPreparation[0].unfinishedTaskCount, 2)
        self.assertEqual(memory.nextAction.task, "Review memoization")
        self.assertIn("2 unfinished task", memory.nextRecommendedActions[-1])

    def test_build_prep_memory_recommends_repeated_gap_without_active_session(self):
        weak_match = RequirementMatch(
            requirement="System design caching",
            category="system_design",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=30,
            matchType="missing",
            reason="No caching design proof.",
        )

        memory = build_prep_memory([_analysis(weak_match)], [])

        self.assertIsNotNone(memory.nextAction)
        self.assertEqual(memory.nextAction.kind, "prepare_repeated_gap")
        self.assertEqual(memory.nextAction.task, "System design caching")

    def test_build_prep_memory_surfaces_today_focus_and_overdue_sessions(self):
        weak_match = RequirementMatch(
            requirement="Azure cloud basics",
            category="cloud",
            importance="high",
            bestEvidence=None,
            evidenceSource="missing",
            score=35,
            matchType="weak",
            reason="Needs stronger cloud evidence.",
        )
        session = PreparationSessionRecord(
            id="prep-3",
            userId="user-1",
            title="Cloud interview sprint",
            status="in_progress",
            plan={
                "dailyPlan": [
                    {
                        "day": 1,
                        "focus": "Azure basics",
                        "goal": "Revise fundamentals.",
                        "tasks": ["Review compute, storage, and network basics"],
                        "output": "Cloud notes",
                    },
                    {
                        "day": 2,
                        "focus": "Scenario practice",
                        "goal": "Answer applied cloud questions.",
                        "tasks": ["Practice AZ-900 scenario answers"],
                        "output": "Scenario answers",
                    },
                ]
            },
            progress={
                "tasks": {"day-1-task-0": "todo", "day-2-task-0": "todo"},
                "confidence": {"day-1": "low"},
            },
            createdAt="2026-06-22T00:00:00Z",
            updatedAt="2026-06-22T00:00:00Z",
        )

        memory = build_prep_memory(
            [_analysis(weak_match)],
            [session],
            reference_time=datetime(2026, 6, 23, tzinfo=timezone.utc),
        )

        self.assertEqual(memory.todayFocus[0].urgency, "overdue")
        self.assertEqual(memory.todayFocus[0].taskId, "day-1-task-0")
        self.assertEqual(memory.attentionSessions[0].overdueTaskCount, 1)
        self.assertEqual(memory.attentionSessions[0].currentPlanDay, 2)
        self.assertEqual(memory.nextAction.kind, "track_today_focus")


if __name__ == "__main__":
    unittest.main()
