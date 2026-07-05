import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def _payload() -> dict:
    return {
        "resumeText": "Python Django React SQL Azure ETL AI agent project experience. " * 2,
        "jobDescriptionText": "Need Python AI Full Stack Engineer with Django, React, SQL, Azure, ETL, and AI guardrails. " * 2,
        "candidateContext": {
            "targetRole": "Python AI Full Stack Engineer",
            "experienceYears": 3,
            "currentStack": ["Python", "Django", "React", "SQL"],
            "targetMarket": "India product companies",
        },
        "llmOptions": {
            "mode": "mock",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
        },
        "preparationPlanDays": 7,
    }


class ScoreOnlyRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def _post_without_usage(self, url: str) -> dict:
        with (
            patch("app.main._enforce_ai_usage", return_value=None),
            patch("app.main._record_ai_usage", return_value=None),
        ):
            response = self.client.post(url, json=_payload())
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_score_route_returns_no_optional_artifacts(self):
        body = self._post_without_usage("/ai/match/score")
        self.assertEqual(body["resumeImprovements"], [])
        self.assertEqual(body["interviewQuestions"], [])
        self.assertEqual(body["crossQuestions"], [])
        self.assertEqual(body["sevenDayPlan"], [])
        self.assertIsNone(body["preparationIntelligence"])
        self.assertIn("Do not generate preparation plans", body["debug"]["promptPreview"])

    def test_legacy_analyze_route_is_score_only(self):
        body = self._post_without_usage("/ai/resume-jd/analyze")
        self.assertEqual(body["resumeImprovements"], [])
        self.assertEqual(body["interviewQuestions"], [])
        self.assertEqual(body["crossQuestions"], [])
        self.assertEqual(body["sevenDayPlan"], [])
        self.assertIsNone(body["preparationIntelligence"])


if __name__ == "__main__":
    unittest.main()
