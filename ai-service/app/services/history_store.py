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
    AnonymousSessionCreateRequest,
    AnonymousSessionRecord,
    AnalysisLookupRequest,
    AnalysisRecord,
    AnalysisSaveRequest,
    JobOpportunityRecord,
    JobOpportunitySaveRequest,
    JobOpportunityStatusUpdateRequest,
    JobDescriptionRecord,
    JobDescriptionSaveRequest,
    OptionalArtifactUsageUpdateRequest,
    PreparationSessionRecord,
    PreparationSessionProgressUpdateRequest,
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


def create_or_touch_anonymous_session(request: AnonymousSessionCreateRequest) -> AnonymousSessionRecord:
    now = _now()
    session_id = request.anonymousSessionId or f"anon_{_id()}"
    with get_connection() as connection:
        existing = connection.execute("SELECT * FROM anonymous_sessions WHERE id = ?", (session_id,)).fetchone()
        if existing:
            connection.execute(
                "UPDATE anonymous_sessions SET last_seen_at = ? WHERE id = ?",
                (now, session_id),
            )
            row = connection.execute("SELECT * FROM anonymous_sessions WHERE id = ?", (session_id,)).fetchone()
            return _anonymous_session_from_row(_require_row(row, "Anonymous session not found after update"))
        connection.execute(
            """
            INSERT INTO anonymous_sessions (id, created_at, last_seen_at, converted_user_id)
            VALUES (?, ?, ?, NULL)
            """,
            (session_id, now, now),
        )
    return AnonymousSessionRecord(id=session_id, createdAt=now, lastSeenAt=now)


def claim_anonymous_session(
    anonymous_session_id: str,
    user_id: str,
    display_name: str | None = None,
    email: str | None = None,
) -> tuple[AnonymousSessionRecord, int]:
    now = _now()
    with get_connection() as connection:
        _get_anonymous_session(connection, anonymous_session_id)
        existing_user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing_user:
            connection.execute(
                "INSERT INTO users (id, display_name, email, created_at) VALUES (?, ?, ?, ?)",
                (user_id, display_name or user_id, email, now),
            )
        connection.execute(
            """
            UPDATE anonymous_sessions
            SET last_seen_at = ?, converted_user_id = ?
            WHERE id = ?
            """,
            (now, user_id, anonymous_session_id),
        )
        update_result = connection.execute(
            """
            UPDATE job_opportunities
            SET user_id = ?, anonymous_session_id = NULL, updated_at = ?
            WHERE anonymous_session_id = ? AND user_id IS NULL
            """,
            (user_id, now, anonymous_session_id),
        )
        row = connection.execute("SELECT * FROM anonymous_sessions WHERE id = ?", (anonymous_session_id,)).fetchone()
    migrated_count = getattr(update_result, "rowcount", 0) or 0
    return _anonymous_session_from_row(_require_row(row, "Anonymous session not found after claim")), migrated_count


def get_workspace_summary(user_id: str) -> WorkspaceSummary:
    with get_connection() as connection:
        user = _get_user(connection, user_id)
        resume_count = _count(connection, "resumes", user_id)
        jd_count = _count(connection, "job_descriptions", user_id)
        analysis_count = _count(connection, "analyses", user_id)
        preparation_count = _count(connection, "preparation_sessions", user_id)
        opportunity_count = _count(connection, "job_opportunities", user_id)
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
        jobOpportunityCount=opportunity_count,
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


def get_resume(user_id: str, resume_id: str) -> ResumeRecord:
    with get_connection() as connection:
        _get_user(connection, user_id)
        row = connection.execute(
            "SELECT * FROM resumes WHERE id = ? AND user_id = ?",
            (resume_id, user_id),
        ).fetchone()
    return _resume_from_row(_require_row(row, "Resume record not found for this user"))


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
                id, user_id, resume_id, job_description_id, title, fingerprint, technical_match_score,
                fit_category, request_json, response_json, optional_artifacts_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.resumeId,
                request.jobDescriptionId,
                request.title,
                request.fingerprint,
                request.response.technicalMatchScore,
                request.response.fitCategory,
                _json_dump(request.request),
                _json_dump(request.response),
                _json_dump(request.optionalArtifacts),
                now,
            ),
        )
    return AnalysisRecord(
        id=record_id,
        userId=request.userId,
        resumeId=request.resumeId,
        jobDescriptionId=request.jobDescriptionId,
        title=request.title,
        fingerprint=request.fingerprint,
        technicalMatchScore=request.response.technicalMatchScore,
        fitCategory=request.response.fitCategory,
        request=request.request,
        response=request.response,
        optionalArtifacts=request.optionalArtifacts,
        createdAt=now,
    )


def lookup_analysis(request: AnalysisLookupRequest) -> AnalysisRecord | None:
    with get_connection() as connection:
        _get_user(connection, request.userId)
        row = connection.execute(
            """
            SELECT * FROM analyses
            WHERE user_id = ? AND fingerprint = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (request.userId, request.fingerprint),
        ).fetchone()
    return _analysis_from_row(row) if row else None


def list_analyses(user_id: str) -> list[AnalysisRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_analysis_from_row(row) for row in rows]


def update_analysis_optional_artifact(record_id: str, request: OptionalArtifactUsageUpdateRequest) -> AnalysisRecord:
    now = _now()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        existing = connection.execute(
            "SELECT * FROM analyses WHERE id = ? AND user_id = ?",
            (record_id, request.userId),
        ).fetchone()
        _require_row(existing, "Analysis record not found for this user")
        optional_artifacts = _json_load(_row_value(existing, "optional_artifacts_json")) if _row_value(existing, "optional_artifacts_json") else {}
        optional_artifacts[request.artifactKey] = {"generatedAt": now}
        connection.execute(
            """
            UPDATE analyses
            SET response_json = ?, optional_artifacts_json = ?
            WHERE id = ? AND user_id = ?
            """,
            (_json_dump(request.response), _json_dump(optional_artifacts), record_id, request.userId),
        )
        row = connection.execute(
            "SELECT * FROM analyses WHERE id = ? AND user_id = ?",
            (record_id, request.userId),
        ).fetchone()
    return _analysis_from_row(_require_row(row, "Analysis record not found after artifact update"))


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
                id, user_id, analysis_id, title, status, plan_json, progress_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.analysisId,
                request.title,
                request.status,
                _json_dump(request.plan),
                _json_dump(request.progress),
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
        progress=request.progress,
        createdAt=now,
        updatedAt=now,
    )


def get_preparation_session(user_id: str, session_id: str) -> PreparationSessionRecord:
    with get_connection() as connection:
        _get_user(connection, user_id)
        row = connection.execute(
            "SELECT * FROM preparation_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
    return _preparation_session_from_row(_require_row(row, "Preparation session not found for this user"))


def update_preparation_session_progress(session_id: str, request: PreparationSessionProgressUpdateRequest) -> PreparationSessionRecord:
    now = _now()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        existing = connection.execute(
            "SELECT * FROM preparation_sessions WHERE id = ? AND user_id = ?",
            (session_id, request.userId),
        ).fetchone()
        _require_row(existing, "Preparation session not found for this user")
        status = request.status or existing["status"]
        connection.execute(
            """
            UPDATE preparation_sessions
            SET status = ?, progress_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (status, _json_dump(request.progress), now, session_id, request.userId),
        )
        row = connection.execute(
            "SELECT * FROM preparation_sessions WHERE id = ? AND user_id = ?",
            (session_id, request.userId),
        ).fetchone()
    return _preparation_session_from_row(_require_row(row, "Preparation session not found after update"))


def list_preparation_sessions(user_id: str) -> list[PreparationSessionRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM preparation_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_preparation_session_from_row(row) for row in rows]


def save_job_opportunity(request: JobOpportunitySaveRequest) -> JobOpportunityRecord:
    now = _now()
    record_id = _id()
    with get_connection() as connection:
        _validate_opportunity_owner(connection, request.userId, request.anonymousSessionId)
        if request.userId and request.resumeId:
            _ensure_owned_record(connection, "resumes", request.resumeId, request.userId)
        if request.userId and request.analysisId:
            _ensure_owned_record(connection, "analyses", request.analysisId, request.userId)
        connection.execute(
            """
            INSERT INTO job_opportunities (
                id, user_id, anonymous_session_id, resume_id, analysis_id, title, company, location,
                url, description, status, technical_match_score, fit_category, analysis_response_json,
                optional_artifacts_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                request.userId,
                request.anonymousSessionId,
                request.resumeId,
                request.analysisId,
                request.title,
                request.company,
                request.location,
                request.url,
                request.description,
                request.status,
                request.technicalMatchScore,
                request.fitCategory,
                _json_dump(request.analysisResponse),
                _json_dump(request.optionalArtifacts),
                now,
                now,
            ),
        )
        row = connection.execute("SELECT * FROM job_opportunities WHERE id = ?", (record_id,)).fetchone()
    return _job_opportunity_from_row(_require_row(row, "Job opportunity not found after save"))


def list_job_opportunities_for_user(user_id: str) -> list[JobOpportunityRecord]:
    with get_connection() as connection:
        _get_user(connection, user_id)
        rows = connection.execute(
            "SELECT * FROM job_opportunities WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_job_opportunity_from_row(row) for row in rows]


def list_job_opportunities_for_anonymous_session(anonymous_session_id: str) -> list[JobOpportunityRecord]:
    with get_connection() as connection:
        _get_anonymous_session(connection, anonymous_session_id)
        rows = connection.execute(
            "SELECT * FROM job_opportunities WHERE anonymous_session_id = ? ORDER BY created_at DESC",
            (anonymous_session_id,),
        ).fetchall()
    return [_job_opportunity_from_row(row) for row in rows]


def update_job_opportunity_status(record_id: str, request: JobOpportunityStatusUpdateRequest) -> JobOpportunityRecord:
    now = _now()
    with get_connection() as connection:
        existing = connection.execute("SELECT * FROM job_opportunities WHERE id = ?", (record_id,)).fetchone()
        _require_row(existing, "Job opportunity not found")
        connection.execute(
            "UPDATE job_opportunities SET status = ?, updated_at = ? WHERE id = ?",
            (request.status, now, record_id),
        )
        row = connection.execute("SELECT * FROM job_opportunities WHERE id = ?", (record_id,)).fetchone()
    return _job_opportunity_from_row(_require_row(row, "Job opportunity not found after update"))


def update_job_opportunity_optional_artifact(record_id: str, request: OptionalArtifactUsageUpdateRequest) -> JobOpportunityRecord:
    now = _now()
    with get_connection() as connection:
        _get_user(connection, request.userId)
        existing = connection.execute(
            "SELECT * FROM job_opportunities WHERE id = ? AND user_id = ?",
            (record_id, request.userId),
        ).fetchone()
        _require_row(existing, "Job opportunity not found for this user")
        optional_artifacts = _json_load(_row_value(existing, "optional_artifacts_json")) if _row_value(existing, "optional_artifacts_json") else {}
        optional_artifacts[request.artifactKey] = {"generatedAt": now}
        connection.execute(
            """
            UPDATE job_opportunities
            SET analysis_response_json = ?, optional_artifacts_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (_json_dump(request.response), _json_dump(optional_artifacts), now, record_id, request.userId),
        )
        row = connection.execute(
            "SELECT * FROM job_opportunities WHERE id = ? AND user_id = ?",
            (record_id, request.userId),
        ).fetchone()
    return _job_opportunity_from_row(_require_row(row, "Job opportunity not found after artifact update"))


def _get_user(connection, user_id: str) -> UserRecord:
    row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_from_row(row)


def _get_anonymous_session(connection, anonymous_session_id: str) -> AnonymousSessionRecord:
    row = connection.execute("SELECT * FROM anonymous_sessions WHERE id = ?", (anonymous_session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Anonymous session not found")
    return _anonymous_session_from_row(row)


def _validate_opportunity_owner(connection, user_id: str | None, anonymous_session_id: str | None) -> None:
    if user_id:
        _get_user(connection, user_id)
    if anonymous_session_id:
        _get_anonymous_session(connection, anonymous_session_id)
    if not user_id and not anonymous_session_id:
        raise HTTPException(status_code=400, detail="Either userId or anonymousSessionId is required")


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


def _anonymous_session_from_row(row: Any) -> AnonymousSessionRecord:
    return AnonymousSessionRecord(
        id=row["id"],
        createdAt=row["created_at"],
        lastSeenAt=row["last_seen_at"],
        convertedUserId=row["converted_user_id"],
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
        fingerprint=row.get("fingerprint") if hasattr(row, "get") else row["fingerprint"],
        technicalMatchScore=row["technical_match_score"],
        fitCategory=row["fit_category"],
        request=_json_model(row["request_json"], AnalyzeRequest),
        response=_json_model(row["response_json"], AnalysisResponse),
        optionalArtifacts=_json_load(_row_value(row, "optional_artifacts_json")) if _row_value(row, "optional_artifacts_json") else {},
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
        progress=_json_load(row["progress_json"]) if _row_value(row, "progress_json") else None,
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _job_opportunity_from_row(row: Any) -> JobOpportunityRecord:
    return JobOpportunityRecord(
        id=row["id"],
        userId=row["user_id"],
        anonymousSessionId=row["anonymous_session_id"],
        resumeId=row["resume_id"],
        analysisId=row["analysis_id"],
        title=row["title"],
        company=row["company"],
        location=row["location"],
        url=row["url"],
        description=row["description"],
        status=row["status"],
        technicalMatchScore=row["technical_match_score"],
        fitCategory=row["fit_category"],
        analysisResponse=_json_model(row["analysis_response_json"], AnalysisResponse),
        optionalArtifacts=_json_load(_row_value(row, "optional_artifacts_json")) if _row_value(row, "optional_artifacts_json") else {},
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


def _row_value(row: Any, key: str):
    if hasattr(row, "get"):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _require_row(row: Any | None, detail: str) -> Any:
    if not row:
        raise HTTPException(status_code=404, detail=detail)
    return row


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid4().hex
