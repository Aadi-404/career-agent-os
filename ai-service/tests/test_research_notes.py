import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.models.history import ResearchNoteSaveRequest, ResearchSource
from app.services.history_store import list_research_notes, save_research_note


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _ResearchConnection:
    def __init__(self):
        self.inserted = None

    def execute(self, query, params=()):
        if "SELECT * FROM users" in query:
            return _Rows([{
                "id": "user-1",
                "display_name": "User 1",
                "email": "user@example.test",
                "role": "member",
                "subscription_tier": "free",
                "subscription_status": "inactive",
                "created_at": "2026-07-03T00:00:00Z",
            }])
        if "INSERT INTO research_notes" in query:
            self.inserted = {
                "id": params[0],
                "user_id": params[1],
                "title": params[2],
                "company": params[3],
                "role_title": params[4],
                "research_type": params[5],
                "summary": params[6],
                "key_signals_json": params[7],
                "preparation_topics_json": params[8],
                "sources_json": params[9],
                "created_at": params[10],
                "updated_at": params[11],
            }
            return _Rows([])
        if "SELECT * FROM research_notes WHERE id" in query:
            return _Rows([self.inserted])
        if "SELECT * FROM research_notes WHERE user_id" in query:
            return _Rows([self.inserted])
        return _Rows([])


@contextmanager
def _fake_connection(connection):
    yield connection


class ResearchNoteTests(unittest.TestCase):
    def test_save_and_list_research_note(self):
        connection = _ResearchConnection()
        request = ResearchNoteSaveRequest(
            userId="user-1",
            title="DemoFin AI interview signals",
            company="DemoFin",
            roleTitle="Python AI Full Stack Engineer",
            researchType="interview",
            summary="Manual research note for expected AI-agent and ETL interview topics.",
            keySignals=["AI-agent guardrails", "ETL reliability"],
            preparationTopics=["tool permissions", "retry design"],
            sources=[ResearchSource(title="Manual interview note", sourceType="manual", note="Collected from mock review.")],
        )

        with patch("app.services.history_store.get_connection", lambda: _fake_connection(connection)):
            saved = save_research_note(request)
            notes = list_research_notes("user-1")

        self.assertEqual(saved.title, "DemoFin AI interview signals")
        self.assertEqual(saved.company, "DemoFin")
        self.assertEqual(saved.keySignals, ["AI-agent guardrails", "ETL reliability"])
        self.assertEqual(saved.preparationTopics, ["tool permissions", "retry design"])
        self.assertEqual(saved.sources[0].title, "Manual interview note")
        self.assertEqual(notes[0].id, saved.id)


if __name__ == "__main__":
    unittest.main()
