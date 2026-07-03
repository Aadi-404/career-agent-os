import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.services.history_store import get_usage_summary, record_usage_event


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _UsageConnection:
    def __init__(self, user_exists=True):
        self.user_exists = user_exists
        self.inserted = None

    def execute(self, query, params=()):
        if "SELECT id FROM users" in query:
            return _Rows([{"id": params[0]}] if self.user_exists else [])
        if "INSERT INTO usage_events" in query:
            self.inserted = params
            return _Rows([])
        return _Rows([])


class _SummaryConnection:
    def execute(self, query, params=()):
        if "SELECT *" in query and "FROM usage_events" in query:
            return _Rows([
                {
                    "id": "usage-1",
                    "user_id": "user-1",
                    "module": "score",
                    "mode": "mock",
                    "provider": "groq",
                    "model": "llama",
                    "estimated_units": 1,
                    "created_at": "2026-07-03T00:00:00Z",
                },
                {
                    "id": "usage-2",
                    "user_id": "user-1",
                    "module": "preparation_plan",
                    "mode": "live",
                    "provider": "gemini",
                    "model": "gemini-2.0-flash",
                    "estimated_units": 2,
                    "created_at": "2026-07-03T00:01:00Z",
                },
            ])
        if "GROUP BY user_id, module" in query:
            return _Rows([
                {"user_id": "user-1", "module": "score", "events": 1, "units": 1},
                {"user_id": "user-1", "module": "preparation_plan", "events": 1, "units": 2},
            ])
        if "SELECT * FROM users" in query:
            return _Rows([{"id": "user-1", "display_name": "User 1", "email": None, "role": "member", "created_at": "2026-07-03T00:00:00Z"}])
        return _Rows([])


@contextmanager
def _fake_connection(connection):
    yield connection


class UsageTrackingTests(unittest.TestCase):
    def test_record_usage_event_drops_unknown_user_reference(self):
        connection = _UsageConnection(user_exists=False)

        with patch("app.services.history_store.get_connection", lambda: _fake_connection(connection)):
            event = record_usage_event("score", user_id="missing-user", mode="mock", provider="groq", model="llama", estimated_units=0)

        self.assertIsNone(event.userId)
        self.assertEqual(event.estimatedUnits, 1)
        self.assertIsNone(connection.inserted[1])
        self.assertEqual(connection.inserted[2], "score")

    def test_usage_summary_aggregates_events_units_modules_and_users(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_SummaryConnection())):
            summary = get_usage_summary(user_id="user-1")

        self.assertEqual(summary.totalEvents, 2)
        self.assertEqual(summary.totalEstimatedUnits, 3)
        self.assertEqual(summary.byModule["score"], 1)
        self.assertEqual(summary.byModule["preparation_plan"], 1)
        self.assertEqual(summary.byUser["user-1"], 2)
        self.assertEqual(len(summary.latestEvents), 2)


if __name__ == "__main__":
    unittest.main()
