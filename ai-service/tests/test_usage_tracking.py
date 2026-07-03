import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException

from app.services.history_store import ensure_usage_quota, get_usage_quota_status, get_usage_summary, record_usage_event


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _UsageConnection:
    def __init__(self, user_exists=True, anonymous_session_exists=False):
        self.user_exists = user_exists
        self.anonymous_session_exists = anonymous_session_exists
        self.inserted = None

    def execute(self, query, params=()):
        if "SELECT id FROM users" in query:
            return _Rows([{"id": params[0]}] if self.user_exists else [])
        if "SELECT id FROM anonymous_sessions" in query:
            return _Rows([{"id": params[0]}] if self.anonymous_session_exists else [])
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
                    "anonymous_session_id": None,
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
                    "anonymous_session_id": None,
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


class _QuotaConnection:
    def __init__(self, tier="free", role="member", used_units=0, anonymous_session_exists=True):
        self.tier = tier
        self.role = role
        self.used_units = used_units
        self.anonymous_session_exists = anonymous_session_exists

    def execute(self, query, params=()):
        if "SELECT * FROM users" in query:
            return _Rows([{
                "id": "user-1",
                "display_name": "User 1",
                "email": None,
                "role": self.role,
                "subscription_tier": self.tier,
                "created_at": "2026-07-03T00:00:00Z",
            }])
        if "SELECT * FROM anonymous_sessions" in query:
            return _Rows([{
                "id": "anon-1",
                "created_at": "2026-07-03T00:00:00Z",
                "last_seen_at": "2026-07-03T00:00:00Z",
                "converted_user_id": None,
            }] if self.anonymous_session_exists else [])
        if "SELECT COALESCE(SUM(estimated_units), 0) AS units" in query:
            return _Rows([{"units": self.used_units}])
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
        self.assertIsNone(connection.inserted[2])
        self.assertEqual(connection.inserted[3], "score")

    def test_record_usage_event_keeps_known_anonymous_session_without_user(self):
        connection = _UsageConnection(user_exists=False, anonymous_session_exists=True)

        with patch("app.services.history_store.get_connection", lambda: _fake_connection(connection)):
            event = record_usage_event("extension_match", anonymous_session_id="anon-1", estimated_units=1)

        self.assertIsNone(event.userId)
        self.assertEqual(event.anonymousSessionId, "anon-1")
        self.assertIsNone(connection.inserted[1])
        self.assertEqual(connection.inserted[2], "anon-1")
        self.assertEqual(connection.inserted[3], "extension_match")

    def test_usage_summary_aggregates_events_units_modules_and_users(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_SummaryConnection())):
            summary = get_usage_summary(user_id="user-1")

        self.assertEqual(summary.totalEvents, 2)
        self.assertEqual(summary.totalEstimatedUnits, 3)
        self.assertEqual(summary.byModule["score"], 1)
        self.assertEqual(summary.byModule["preparation_plan"], 1)
        self.assertEqual(summary.byUser["user-1"], 2)
        self.assertEqual(len(summary.latestEvents), 2)
        self.assertEqual(summary.quota.tier, "free")

    def test_free_usage_quota_reports_monthly_remaining_units(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_QuotaConnection(used_units=12))):
            status = get_usage_quota_status("user-1")

        self.assertEqual(status.tier, "free")
        self.assertEqual(status.limitUnits, 50)
        self.assertEqual(status.usedUnits, 12)
        self.assertEqual(status.remainingUnits, 38)
        self.assertFalse(status.unlimited)

    def test_usage_quota_blocks_when_requested_units_exceed_remaining(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_QuotaConnection(used_units=49))):
            with self.assertRaises(HTTPException) as context:
                ensure_usage_quota("interview_questions", "user-1", estimated_units=2)

        self.assertEqual(context.exception.status_code, 429)
        self.assertIn("quota exceeded", context.exception.detail)

    def test_admin_usage_quota_is_unlimited(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_QuotaConnection(role="admin", used_units=999))):
            status = ensure_usage_quota("score", "user-1", estimated_units=500)

        self.assertTrue(status.unlimited)
        self.assertIsNone(status.limitUnits)

    def test_anonymous_session_usage_quota_uses_anonymous_tier(self):
        with patch("app.services.history_store.get_connection", lambda: _fake_connection(_QuotaConnection(used_units=8))):
            status = ensure_usage_quota("extension_match", anonymous_session_id="anon-1", estimated_units=2)

        self.assertEqual(status.tier, "anonymous")
        self.assertEqual(status.anonymousSessionId, "anon-1")
        self.assertEqual(status.limitUnits, 10)
        self.assertEqual(status.remainingUnits, 2)


if __name__ == "__main__":
    unittest.main()
