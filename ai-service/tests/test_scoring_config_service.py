import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.services.scoring_config_service import recommend_scoring_calibration


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, feedback_rows):
        self.feedback_rows = feedback_rows

    def execute(self, query, params=()):
        if "FROM scoring_calibration_configs" in query:
            return _Rows([])
        if "FROM match_feedback" in query:
            return _Rows(self.feedback_rows)
        return _Rows([])


@contextmanager
def _fake_connection(feedback_rows):
    yield _Connection(feedback_rows)


class ScoringConfigServiceTests(unittest.TestCase):
    def test_recommendation_waits_for_enough_labels(self):
        rows = [{"score_accuracy": "too_low", "expected_fit": "good", "outcome": "applied", "algorithm_score": 55}]

        with patch("app.services.scoring_config_service.get_connection", lambda: _fake_connection(rows)):
            recommendation = recommend_scoring_calibration("user-1", ".NET")

        self.assertEqual(recommendation.confidence, "low")
        self.assertEqual(recommendation.sampleSize, 1)
        self.assertEqual(recommendation.currentWeights, recommendation.suggestedWeights)
        self.assertEqual(recommendation.changes, [])

    def test_recommendation_moves_weights_when_scores_trend_low(self):
        rows = [
            {"score_accuracy": "too_low", "expected_fit": "good", "outcome": "applied", "algorithm_score": 55},
            {"score_accuracy": "too_low", "expected_fit": "good", "outcome": "shortlisted", "algorithm_score": 58},
            {"score_accuracy": "too_low", "expected_fit": "strong", "outcome": "interview", "algorithm_score": 62},
            {"score_accuracy": "too_low", "expected_fit": "good", "outcome": "applied", "algorithm_score": 54},
            {"score_accuracy": "too_low", "expected_fit": "partial", "outcome": "applied", "algorithm_score": 50},
            {"score_accuracy": "accurate", "expected_fit": "partial", "outcome": "applied", "algorithm_score": 64},
            {"score_accuracy": "accurate", "expected_fit": "weak", "outcome": "not_applied", "algorithm_score": 38},
            {"score_accuracy": "too_high", "expected_fit": "weak", "outcome": "rejected", "algorithm_score": 78},
        ]

        with patch("app.services.scoring_config_service.get_connection", lambda: _fake_connection(rows)):
            recommendation = recommend_scoring_calibration("user-1", ".NET")

        self.assertEqual(recommendation.confidence, "medium")
        self.assertEqual(sum(recommendation.suggestedWeights.values()), 100)
        self.assertGreater(recommendation.suggestedWeights["dynamicRequirementFit"], recommendation.currentWeights["dynamicRequirementFit"])
        self.assertGreater(recommendation.suggestedWeights["projectRelevance"], recommendation.currentWeights["projectRelevance"])
        self.assertTrue(recommendation.changes)


if __name__ == "__main__":
    unittest.main()
