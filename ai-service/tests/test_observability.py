import unittest

from fastapi.testclient import TestClient

from app.main import app


class ObservabilityTests(unittest.TestCase):
    def test_health_response_includes_request_id(self):
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("x-request-id"))

    def test_incoming_request_id_is_preserved(self):
        client = TestClient(app)

        response = client.get("/health", headers={"X-Request-ID": "test-request-123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-request-id"), "test-request-123")


if __name__ == "__main__":
    unittest.main()
