import json
from uuid import uuid4
from datetime import UTC, datetime
from typing import Any

from app.db import get_connection
from app.models.scoring_config import (
    ROLE_FAMILIES,
    ScoringCalibrationAuditRecord,
    ScoringCalibrationConfig,
    ScoringCalibrationListResponse,
    ScoringCalibrationRecommendation,
    ScoringCalibrationRestoreRequest,
    ScoringCalibrationUpdateRequest,
)


BASE_WEIGHTS_2_TO_4 = {
    "experienceFit": 10,
    "dynamicRequirementFit": 30,
    "projectRelevance": 20,
    "technicalDepth": 15,
    "deliveryReadiness": 15,
    "systemReadiness": 5,
    "problemSolving": 5,
}

DEFAULT_ROLE_WEIGHTS = {
    ".NET": {
        "experienceFit": 10,
        "dynamicRequirementFit": 30,
        "projectRelevance": 18,
        "technicalDepth": 18,
        "deliveryReadiness": 16,
        "systemReadiness": 5,
        "problemSolving": 3,
    },
    "Java": {
        "experienceFit": 10,
        "dynamicRequirementFit": 30,
        "projectRelevance": 18,
        "technicalDepth": 18,
        "deliveryReadiness": 14,
        "systemReadiness": 7,
        "problemSolving": 3,
    },
    "Python": {
        "experienceFit": 10,
        "dynamicRequirementFit": 30,
        "projectRelevance": 20,
        "technicalDepth": 18,
        "deliveryReadiness": 12,
        "systemReadiness": 5,
        "problemSolving": 5,
    },
    "Frontend": {
        "experienceFit": 8,
        "dynamicRequirementFit": 32,
        "projectRelevance": 24,
        "technicalDepth": 18,
        "deliveryReadiness": 10,
        "systemReadiness": 3,
        "problemSolving": 5,
    },
    "Data/AI": {
        "experienceFit": 8,
        "dynamicRequirementFit": 32,
        "projectRelevance": 18,
        "technicalDepth": 20,
        "deliveryReadiness": 12,
        "systemReadiness": 5,
        "problemSolving": 5,
    },
    "Cloud/DevOps": {
        "experienceFit": 8,
        "dynamicRequirementFit": 30,
        "projectRelevance": 14,
        "technicalDepth": 18,
        "deliveryReadiness": 20,
        "systemReadiness": 7,
        "problemSolving": 3,
    },
    "General Software": BASE_WEIGHTS_2_TO_4,
}


def list_scoring_calibrations(user_id: str) -> ScoringCalibrationListResponse:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    saved = {_row_value(row, "role_family"): _config_from_row(row) for row in rows}
    configs = [
        saved.get(role_family) or ScoringCalibrationConfig(
            userId=user_id,
            roleFamily=role_family,
            categoryWeights=DEFAULT_ROLE_WEIGHTS[role_family],
            isDefault=True,
            updatedAt=None,
        )
        for role_family in ROLE_FAMILIES
    ]
    return ScoringCalibrationListResponse(userId=user_id, configs=configs)


def save_scoring_calibration(request: ScoringCalibrationUpdateRequest) -> ScoringCalibrationConfig:
    now = _now()
    family = normalize_role_family(request.roleFamily)
    with get_connection() as connection:
        previous_row = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ? AND role_family = ?",
            (request.userId, family),
        ).fetchone()
        previous_weights = (
            json.loads(previous_row["category_weights_json"])
            if previous_row
            else DEFAULT_ROLE_WEIGHTS.get(family, DEFAULT_ROLE_WEIGHTS["General Software"])
        )
        connection.execute(
            """
            INSERT INTO scoring_calibration_configs (user_id, role_family, category_weights_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, role_family)
            DO UPDATE SET category_weights_json = EXCLUDED.category_weights_json, updated_at = EXCLUDED.updated_at
            """,
            (request.userId, family, json.dumps(request.categoryWeights, sort_keys=True), now),
        )
        connection.execute(
            """
            INSERT INTO scoring_calibration_audit (
                id, user_id, role_family, previous_weights_json, new_weights_json, change_source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _id(),
                request.userId,
                family,
                json.dumps(previous_weights, sort_keys=True),
                json.dumps(request.categoryWeights, sort_keys=True),
                request.changeSource,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ? AND role_family = ?",
            (request.userId, family),
        ).fetchone()
    return _config_from_row(row)


def list_scoring_calibration_audit(user_id: str, role_family: str | None = None) -> list[ScoringCalibrationAuditRecord]:
    family = normalize_role_family(role_family) if role_family else None
    with get_connection() as connection:
        if family:
            rows = connection.execute(
                """
                SELECT * FROM scoring_calibration_audit
                WHERE user_id = ? AND role_family = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id, family),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM scoring_calibration_audit
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id,),
            ).fetchall()
    return [_audit_from_row(row) for row in rows]


def restore_scoring_calibration(request: ScoringCalibrationRestoreRequest) -> ScoringCalibrationConfig:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM scoring_calibration_audit WHERE id = ? AND user_id = ?",
            (request.auditId, request.userId),
        ).fetchone()
    if not row:
        raise ValueError("Scoring calibration audit record not found")
    return save_scoring_calibration(
        ScoringCalibrationUpdateRequest(
            userId=request.userId,
            roleFamily=row["role_family"],
            categoryWeights=json.loads(row["previous_weights_json"]),
            changeSource=f"restore:{request.auditId}",
        )
    )


def recommend_scoring_calibration(user_id: str, role_family: str) -> ScoringCalibrationRecommendation:
    family = normalize_role_family(role_family)
    current = _current_or_default_weights(user_id, family)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT score_accuracy, expected_fit, outcome, algorithm_score
            FROM match_feedback
            WHERE user_id = ? AND COALESCE(role_family, 'General Software') = ?
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (user_id, family),
        ).fetchall()
    total = len(rows)
    too_low = sum(1 for row in rows if row["score_accuracy"] == "too_low")
    too_high = sum(1 for row in rows if row["score_accuracy"] == "too_high")
    accurate = sum(1 for row in rows if row["score_accuracy"] == "accurate")
    suggested = dict(current)
    changes: list[str] = []

    if total < 8:
        return ScoringCalibrationRecommendation(
            userId=user_id,
            roleFamily=family,
            currentWeights=current,
            suggestedWeights=suggested,
            confidence="low",
            sampleSize=total,
            reason="Collect at least 8 labelled matches in this role family before applying weight recommendations.",
            changes=[],
        )

    if too_low > max(accurate, too_high) and too_low >= 3:
        _move_weight(suggested, "experienceFit", "dynamicRequirementFit", 2, changes)
        _move_weight(suggested, "problemSolving", "projectRelevance", 1, changes)
        _move_weight(suggested, "systemReadiness", "technicalDepth", 1, changes)
        reason = "Feedback says scores are often too low, so the suggestion gives more credit to semantic requirement fit, project proof, and technical depth."
    elif too_high > max(accurate, too_low) and too_high >= 3:
        _move_weight(suggested, "dynamicRequirementFit", "experienceFit", 2, changes)
        _move_weight(suggested, "projectRelevance", "deliveryReadiness", 1, changes)
        _move_weight(suggested, "technicalDepth", "systemReadiness", 1, changes)
        reason = "Feedback says scores are often too high, so the suggestion increases experience, delivery, and system-readiness pressure."
    else:
        reason = "Feedback is balanced or mostly accurate; no major weight shift is recommended yet."

    suggested = _align_weights(suggested, current)
    confidence = "high" if total >= 25 else "medium"
    if not changes:
        confidence = "medium" if total >= 25 else "low"

    return ScoringCalibrationRecommendation(
        userId=user_id,
        roleFamily=family,
        currentWeights=current,
        suggestedWeights=suggested,
        confidence=confidence,
        sampleSize=total,
        reason=reason,
        changes=changes,
    )


def get_effective_weights(user_id: str | None, role_family: str | None, fallback_weights: dict[str, int]) -> dict[str, int]:
    if not user_id:
        return fallback_weights
    family = normalize_role_family(role_family)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ? AND role_family = ?",
            (user_id, family),
        ).fetchone()
    if not row:
        default = DEFAULT_ROLE_WEIGHTS.get(family)
        return _align_weights(default or fallback_weights, fallback_weights)
    return _align_weights(json.loads(row["category_weights_json"]), fallback_weights)


def _current_or_default_weights(user_id: str, role_family: str) -> dict[str, int]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ? AND role_family = ?",
            (user_id, role_family),
        ).fetchone()
    if row:
        return json.loads(row["category_weights_json"])
    return DEFAULT_ROLE_WEIGHTS.get(role_family, DEFAULT_ROLE_WEIGHTS["General Software"])


def _move_weight(weights: dict[str, int], source: str, target: str, amount: int, changes: list[str]) -> None:
    if source not in weights or target not in weights or weights[source] < amount:
        return
    weights[source] -= amount
    weights[target] += amount
    changes.append(f"Move {amount}% from {source} to {target}.")


def normalize_role_family(role_family: str | None) -> str:
    if role_family in ROLE_FAMILIES:
        return role_family
    return "General Software"


def _align_weights(candidate: dict[str, int], fallback_weights: dict[str, int]) -> dict[str, int]:
    aligned = {category: int(candidate.get(category, fallback_weight)) for category, fallback_weight in fallback_weights.items()}
    total = sum(aligned.values())
    if total == 100:
        return aligned
    if total <= 0:
        return fallback_weights
    normalized = {category: round((weight / total) * 100) for category, weight in aligned.items()}
    drift = 100 - sum(normalized.values())
    if normalized:
        first_key = next(iter(normalized))
        normalized[first_key] += drift
    return normalized


def _config_from_row(row: Any) -> ScoringCalibrationConfig:
    return ScoringCalibrationConfig(
        userId=row["user_id"],
        roleFamily=row["role_family"],
        categoryWeights=json.loads(row["category_weights_json"]),
        isDefault=False,
        updatedAt=row["updated_at"],
    )


def _audit_from_row(row: Any) -> ScoringCalibrationAuditRecord:
    return ScoringCalibrationAuditRecord(
        id=row["id"],
        userId=row["user_id"],
        roleFamily=row["role_family"],
        previousWeights=json.loads(row["previous_weights_json"]),
        newWeights=json.loads(row["new_weights_json"]),
        changeSource=row["change_source"],
        createdAt=row["created_at"],
    )


def _id() -> str:
    return f"audit_{uuid4().hex[:12]}"


def _row_value(row: Any, key: str):
    if hasattr(row, "get"):
        return row.get(key)
    return row[key]


def _now() -> str:
    return datetime.now(UTC).isoformat()
