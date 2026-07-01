import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import _authorize_admin, _authorize_user, settings
from app.models.history import UserRecord


class AuthGuardTests(unittest.TestCase):
    def setUp(self):
        self.original_required = settings.require_user_auth
        settings.require_user_auth = True

    def tearDown(self):
        settings.require_user_auth = self.original_required

    def test_requires_session_token_when_enabled(self):
        with self.assertRaises(HTTPException) as context:
            _authorize_user("user-1", None)

        self.assertEqual(context.exception.status_code, 401)

    def test_rejects_token_for_different_user(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-2", displayName="User 2", createdAt="2026-06-30T00:00:00Z")):
            with self.assertRaises(HTTPException) as context:
                _authorize_user("user-1", "token")

        self.assertEqual(context.exception.status_code, 403)

    def test_allows_matching_session_token(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", createdAt="2026-06-30T00:00:00Z")):
            _authorize_user("user-1", "token")

    def test_admin_guard_rejects_member(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", role="member", createdAt="2026-06-30T00:00:00Z")):
            with self.assertRaises(HTTPException) as context:
                _authorize_admin("token")

        self.assertEqual(context.exception.status_code, 403)

    def test_admin_guard_allows_admin(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="admin-1", displayName="Admin 1", role="admin", createdAt="2026-06-30T00:00:00Z")):
            _authorize_admin("token")


if __name__ == "__main__":
    unittest.main()
