import unittest

from app.services.history_store import _hash_password, _verify_password


class PasswordAuthTests(unittest.TestCase):
    def test_hash_password_uses_salt(self):
        first = _hash_password("correct horse battery staple")
        second = _hash_password("correct horse battery staple")

        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("pbkdf2_sha256$120000$"))

    def test_verify_password(self):
        stored = _hash_password("correct horse battery staple")

        self.assertTrue(_verify_password("correct horse battery staple", stored))
        self.assertFalse(_verify_password("wrong password", stored))
        self.assertFalse(_verify_password("correct horse battery staple", None))
        self.assertFalse(_verify_password("correct horse battery staple", "unsupported$hash"))


if __name__ == "__main__":
    unittest.main()
