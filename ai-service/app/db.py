import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv


DEFAULT_POSTGRES_DB = "careerAgentOS"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

load_dotenv(ENV_PATH)


class DatabaseConnection:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def execute(self, query: str, params: tuple[Any, ...] = ()):
        query = query.replace("?", "%s")
        return self.connection.execute(query, params)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.connection.execute(statement)

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


@contextmanager
def get_connection() -> Iterator[DatabaseConnection]:
    connection = _postgres_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _postgres_connection() -> DatabaseConnection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("PostgreSQL support requires psycopg. Run: pip install -r requirements.txt") from exc

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        connection = psycopg.connect(database_url, row_factory=dict_row)
    else:
        connection = psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", DEFAULT_POSTGRES_DB),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            row_factory=dict_row,
        )
    return DatabaseConnection(connection)


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(_postgres_schema())


def _postgres_schema() -> str:
    return """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
            WHERE email IS NOT NULL AND email != '';

            CREATE TABLE IF NOT EXISTS anonymous_sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                converted_user_id TEXT REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_anonymous_sessions_last_seen
            ON anonymous_sessions(last_seen_at DESC);

            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_user_sessions_user_seen
            ON user_sessions(user_id, last_seen_at DESC);

            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                normalized_text TEXT,
                structured_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_resumes_user_created
            ON resumes(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS job_descriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                company TEXT,
                raw_text TEXT NOT NULL,
                normalized_text TEXT,
                parsed_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_created
            ON job_descriptions(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                resume_id TEXT REFERENCES resumes(id) ON DELETE SET NULL,
                job_description_id TEXT REFERENCES job_descriptions(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                fingerprint TEXT,
                technical_match_score INTEGER NOT NULL,
                fit_category TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_user_created
            ON analyses(user_id, created_at DESC);

            ALTER TABLE analyses
            ADD COLUMN IF NOT EXISTS fingerprint TEXT;

            ALTER TABLE analyses
            ADD COLUMN IF NOT EXISTS optional_artifacts_json TEXT;

            CREATE INDEX IF NOT EXISTS idx_analyses_user_fingerprint
            ON analyses(user_id, fingerprint)
            WHERE fingerprint IS NOT NULL;

            CREATE TABLE IF NOT EXISTS preparation_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                progress_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_preparation_sessions_user_created
            ON preparation_sessions(user_id, created_at DESC);

            ALTER TABLE preparation_sessions
            ADD COLUMN IF NOT EXISTS progress_json TEXT;

            CREATE TABLE IF NOT EXISTS job_opportunities (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                anonymous_session_id TEXT REFERENCES anonymous_sessions(id) ON DELETE CASCADE,
                resume_id TEXT REFERENCES resumes(id) ON DELETE SET NULL,
                analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                url TEXT,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                technical_match_score INTEGER,
                fit_category TEXT,
                analysis_response_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (user_id IS NOT NULL OR anonymous_session_id IS NOT NULL)
            );

            CREATE INDEX IF NOT EXISTS idx_job_opportunities_user_created
            ON job_opportunities(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_job_opportunities_anonymous_created
            ON job_opportunities(anonymous_session_id, created_at DESC);

            ALTER TABLE job_opportunities
            ADD COLUMN IF NOT EXISTS optional_artifacts_json TEXT;
            """
