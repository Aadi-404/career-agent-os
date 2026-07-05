import unittest

from app.models.analysis import AnalyzeRequest, CandidateContext
from app.services.prompt_builder import build_analysis_prompt, build_full_analysis_prompt, build_score_analysis_prompt


def _request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText="Python Django React SQL Azure ETL AI agent project experience. " * 2,
        jobDescriptionText="Need Python AI Full Stack Engineer with Django, React, SQL, Azure, ETL, and AI guardrails. " * 2,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "React", "SQL"],
            targetMarket="India product companies",
        ),
        preparationPlanDays=7,
    )


class PromptBuilderTests(unittest.TestCase):
    def test_default_analysis_prompt_is_score_only(self):
        prompt = build_analysis_prompt(_request())

        self.assertIn("produce only the resume-to-JD scoring evidence", prompt)
        self.assertIn('"resumeImprovements": []', prompt)
        self.assertIn('"interviewQuestions": []', prompt)
        self.assertIn('"crossQuestions": []', prompt)
        self.assertIn('"sevenDayPlan": []', prompt)
        self.assertIn("must be empty arrays", prompt)
        self.assertNotIn("Generate resume improvements", prompt)
        self.assertNotIn("Give at least 8 interview questions", prompt)
        self.assertNotIn("Preparation plan length: 7 days", prompt)

    def test_explicit_score_prompt_matches_default(self):
        self.assertEqual(build_analysis_prompt(_request()), build_score_analysis_prompt(_request()))

    def test_legacy_full_prompt_is_explicit_only(self):
        prompt = build_full_analysis_prompt(_request())

        self.assertIn("legacy full analysis", prompt)
        self.assertIn("Preparation plan length: 7 days", prompt)
        self.assertIn('"resumeImprovements": [', prompt)
        self.assertIn('"interviewQuestions": [', prompt)
        self.assertIn('"crossQuestions": [', prompt)
        self.assertIn('"sevenDayPlan": [', prompt)


if __name__ == "__main__":
    unittest.main()
