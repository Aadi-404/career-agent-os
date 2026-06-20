import json
from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic_core import from_json

from app.db import get_connection
from app.models.analysis import AnalysisResponse, AnalyzeRequest, PreparationIntelligence
from app.models.history import (
    AnalysisRecord,
    AnalysisSaveRequest,
    JobDescriptionRecord,
    JobDescriptionSaveRequest,
    PreparationSessionRecord,
    PreparationSessionSaveRequest,
    ResumeRecord,
    ResumeSaveRequest,
    UserCreateRequest,
    UserRecord,
    WorkspaceSummary,
)
from app.models.jd_parse import ParsedJobDescription
from app.models.resume_normalize import StructuredResume


def create_or_update_user(request: UserCreateRequest) -> UserRecord:
    now = _now()
    with get_connection() as connection:
        existing = connection.execute("SELECT * FROM users WHERE id = ?", (request.userId,)).fetchone()
        if existing:
            connection.execute(
                "UPDATE users SET display_name = ?, email = ? WHERE id = ?",
                (request.displayName, request.email, request.userId),
            )
            row = connection.execute("SELECT * FROM users WHERE id = ?", (request.userId,)).fetchone()
            return _user_from_row(_require_row(row, "User not found after update"))

        try:
            connection.execute(
                "INSERT INTO users (id, display_name, email, created_at) VALUES (?, ?, ?, ?)",
                (request.userId, request.displayName, request.email, now),
            )
        except Exception as exc:
            if not isinstance(exc, IntegrityError) and exc.__class__.__name__ != "UniqueViolation":
                raise
            raise HTTPException(status_code=409, detail="A user with this email already exists") from exc
    return UserRecord(id=request.userId, displayName=request.displayName, email=request.email, createdAt=now)


def get_workspace_summary(user_id: str) -> WorkspaceSummary:
    with get_connection() as connection:
        user = _get_user(connection, user_id)
        resume_count = _count(connection, "resumes", user_id)
        jd_count = _count(connection, "job_descriptions", user_id)
        analysis_count = _count(connection, "analyses", user_id)
        preparation_count = _count(connection, "preparation_sessions", user_id)
        latest_analysis_row = connection.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    latest_analysis = _analysis_from_row(latest_analysis_row) if latest_analysis_row else None
    return WorkspaceSummary(
        user=user,
        resumeCount=resume_count,
        jobDescriptionCount=jd_count,
        analysisCount=analysis_count,
        preparationSessionCount=preparation_count,
        latestAnalysis=latest_analysis,
    )


def save_resume(request: ResumeSaveRequest) -> ResumeRecord:
    now = _now()
    record_id = _id()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        connection.execute(
            """
            INSERT INTO resumes (
                id, user_id, title, source, raw_text, normalized_text, structured_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.title,
                request.source,
                request.rawText,
                request.normalizedText,
                _json_dump(request.structuredResume),
                now,
                now,
            ),
        )
    return ResumeRecord(
        id=record_id,
        userId=request.userId,
        title=request.title,
        source=request.source,
        rawText=request.rawText,
        normalizedText=request.normalizedText,
        structuredResume=request.structuredResume,
        createdAt=now,
        updatedAt=now,
    )


def list_resumes(user_id: str) -> list[ResumeRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM resumes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_resume_from_row(row) for row in rows]


def save_job_description(request: JobDescriptionSaveRequest) -> JobDescriptionRecord:
    now = _now()
    record_id = _id()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        connection.execute(
            """
            INSERT INTO job_descriptions (
                id, user_id, title, company, raw_text, normalized_text, parsed_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.title,
                request.company,
                request.rawText,
                request.normalizedText,
                _json_dump(request.parsedJobDescription),
                now,
                now,
            ),
        )
    return JobDescriptionRecord(
        id=record_id,
        userId=request.userId,
        title=request.title,
        company=request.company,
        rawText=request.rawText,
        normalizedText=request.normalizedText,
        parsedJobDescription=request.parsedJobDescription,
        createdAt=now,
        updatedAt=now,
    )


def list_job_descriptions(user_id: str) -> list[JobDescriptionRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM job_descriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_job_description_from_row(row) for row in rows]


def save_analysis(request: AnalysisSaveRequest) -> AnalysisRecord:
    now = _now()
    record_id = _id()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        if request.resumeId:
            _ensure_owned_record(connection, "resumes", request.resumeId, request.userId)
        if request.jobDescriptionId:
            _ensure_owned_record(connection, "job_descriptions", request.jobDescriptionId, request.userId)
        connection.execute(
            """
            INSERT INTO analyses (
                id, user_id, resume_id, job_description_id, title, technical_match_score,
                fit_category, request_json, response_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.resumeId,
                request.jobDescriptionId,
                request.title,
                request.response.technicalMatchScore,
                request.response.fitCategory,
                _json_dump(request.request),
                _json_dump(request.response),
                now,
            ),
        )
    return AnalysisRecord(
        id=record_id,
        userId=request.userId,
        resumeId=request.resumeId,
        jobDescriptionId=request.jobDescriptionId,
        title=request.title,
        technicalMatchScore=request.response.technicalMatchScore,
        fitCategory=request.response.fitCategory,
        request=request.request,
        response=request.response,
        createdAt=now,
    )


def list_analyses(user_id: str) -> list[AnalysisRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_analysis_from_row(row) for row in rows]


def save_preparation_session(request: PreparationSessionSaveRequest) -> PreparationSessionRecord:
    now = _now()
    record_id = _id()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        if request.analysisId:
            _ensure_owned_record(connection, "analyses", request.analysisId, request.userId)
        connection.execute(
            """
            INSERT INTO preparation_sessions (
                id, user_id, analysis_id, title, status, plan_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.analysisId,
                request.title,
                request.status,
                _json_dump(request.plan),
                now,
                now,
            ),
        )
    return PreparationSessionRecord(
        id=record_id,
        userId=request.userId,
        analysisId=request.analysisId,
        title=request.title,
        status=request.status,
        plan=request.plan,
        createdAt=now,
        updatedAt=now,
    )


def list_preparation_sessions(user_id: str) -> list[PreparationSessionRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM preparation_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_preparation_session_from_row(row) for row in rows]


def _get_user(connection, user_id: str) -> UserRecord:
    row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_from_row(row)


def _ensure_owned_record(connection, table: str, record_id: str, user_id: str) -> None:
    row = connection.execute(
        f"SELECT id FROM {table} WHERE id = ? AND user_id = ?",
        (record_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"{table} record not found for this user")


def _count(connection, table: str, user_id: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE user_id = ?", (user_id,)).fetchone()
    return int(row["count"])


def _user_from_row(row: Any) -> UserRecord:
    return UserRecord(
        id=row["id"],
        displayName=row["display_name"],
        email=row["email"],
        createdAt=row["created_at"],
    )


def _resume_from_row(row: Any) -> ResumeRecord:
    return ResumeRecord(
        id=row["id"],
        userId=row["user_id"],
        title=row["title"],
        source=row["source"],
        rawText=row["raw_text"],
        normalizedText=row["normalized_text"],
        structuredResume=_json_model(row["structured_json"], StructuredResume),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _job_description_from_row(row: Any) -> JobDescriptionRecord:
    return JobDescriptionRecord(
        id=row["id"],
        userId=row["user_id"],
        title=row["title"],
        company=row["company"],
        rawText=row["raw_text"],
        normalizedText=row["normalized_text"],
        parsedJobDescription=_json_model(row["parsed_json"], ParsedJobDescription),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _analysis_from_row(row: Any) -> AnalysisRecord:
    return AnalysisRecord(
        id=row["id"],
        userId=row["user_id"],
        resumeId=row["resume_id"],
        jobDescriptionId=row["job_description_id"],
        title=row["title"],
        technicalMatchScore=row["technical_match_score"],
        fitCategory=row["fit_category"],
        request=_json_model(row["request_json"], AnalyzeRequest),
        response=_json_model(row["response_json"], AnalysisResponse),
        createdAt=row["created_at"],
    )


def _preparation_session_from_row(row: Any) -> PreparationSessionRecord:
    return PreparationSessionRecord(
        id=row["id"],
        userId=row["user_id"],
        analysisId=row["analysis_id"],
        title=row["title"],
        status=row["status"],
        plan=_json_model(row["plan_json"], PreparationIntelligence) or _json_load(row["plan_json"]),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _json_dump(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    return json.dumps(value)


def _json_model(value: str | None, model_type):
    if not value:
        return None
    if isinstance(value, dict):
        return model_type.model_validate(value)
    return model_type.model_validate_json(value)


def _json_load(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        return from_json(value)
    return json.loads(value)


def _require_row(row: Any | None, detail: str) -> Any:
    if not row:
        raise HTTPException(status_code=404, detail=detail)
    return row


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid4().hex
