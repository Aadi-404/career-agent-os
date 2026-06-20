import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "career_agent_os.sqlite3"
DEFAULT_POSTGRES_DB = "careerAgentOS"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

load_dotenv(ENV_PATH)


class DatabaseConnection:
    def __init__(self, connection: Any, provider: str) -> None:
        self.connection = connection
        self.provider = provider

    def execute(self, query: str, params: tuple[Any, ...] = ()):
        if self.provider == "postgres":
            query = query.replace("?", "%s")
        return self.connection.execute(query, params)

    def executescript(self, script: str) -> None:
        if self.provider == "postgres":
            for statement in script.split(";"):
                if statement.strip():
                    self.connection.execute(statement)
            return
        self.connection.executescript(script)

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


def get_database_provider() -> str:
    return os.getenv("CAREER_AGENT_DB_PROVIDER", "sqlite").strip().lower()


def get_database_path() -> Path:
    configured_path = os.getenv("CAREER_AGENT_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_DB_PATH


@contextmanager
def get_connection() -> Iterator[DatabaseConnection]:
    provider = get_database_provider()
    if provider == "postgres":
        connection = _postgres_connection()
    else:
        connection = _sqlite_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _sqlite_connection() -> DatabaseConnection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection, "sqlite")


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
    return DatabaseConnection(connection, "postgres")


def initialize_database() -> None:
    with get_connection() as connection:
        if connection.provider == "postgres":
            connection.executescript(_postgres_schema())
        else:
            connection.executescript(_sqlite_schema())


def _sqlite_schema() -> str:
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

            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                normalized_text TEXT,
                structured_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_resumes_user_created
            ON resumes(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS job_descriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                raw_text TEXT NOT NULL,
                normalized_text TEXT,
                parsed_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_created
            ON job_descriptions(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                resume_id TEXT,
                job_description_id TEXT,
                title TEXT NOT NULL,
                technical_match_score INTEGER NOT NULL,
                fit_category TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE SET NULL,
                FOREIGN KEY(job_description_id) REFERENCES job_descriptions(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_user_created
            ON analyses(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS preparation_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                analysis_id TEXT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_preparation_sessions_user_created
            ON preparation_sessions(user_id, created_at DESC);
            """


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
                technical_match_score INTEGER NOT NULL,
                fit_category TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_user_created
            ON analyses(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS preparation_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_preparation_sessions_user_created
            ON preparation_sessions(user_id, created_at DESC);
            """
