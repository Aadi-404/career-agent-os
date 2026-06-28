import json
from datetime import UTC, datetime
from typing import Any

from app.db import get_connection
from app.models.scoring_config import ROLE_FAMILIES, ScoringCalibrationConfig, ScoringCalibrationListResponse, ScoringCalibrationUpdateRequest


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
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO scoring_calibration_configs (user_id, role_family, category_weights_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, role_family)
            DO UPDATE SET category_weights_json = EXCLUDED.category_weights_json, updated_at = EXCLUDED.updated_at
            """,
            (request.userId, request.roleFamily, json.dumps(request.categoryWeights, sort_keys=True), now),
        )
        row = connection.execute(
            "SELECT * FROM scoring_calibration_configs WHERE user_id = ? AND role_family = ?",
            (request.userId, request.roleFamily),
        ).fetchone()
    return _config_from_row(row)


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


def _row_value(row: Any, key: str):
    if hasattr(row, "get"):
        return row.get(key)
    return row[key]


def _now() -> str:
    return datetime.now(UTC).isoformat()
