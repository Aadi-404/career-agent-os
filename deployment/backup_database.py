import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = ROOT / "ai-service"
sys.path.insert(0, str(AI_SERVICE_DIR))

from app.db import get_connection, initialize_database  # noqa: E402


TABLES = [
    "users",
    "anonymous_sessions",
    "user_sessions",
    "resumes",
    "job_descriptions",
    "analyses",
    "preparation_sessions",
    "job_opportunities",
    "extension_validation_runs",
    "match_feedback",
    "scoring_calibration_configs",
    "scoring_calibration_audit",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Career Agent OS PostgreSQL data to JSON.")
    parser.add_argument("--output", default="", help="Output JSON path. Defaults to deployment/backups/<timestamp>.json.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON for review.")
    args = parser.parse_args()

    initialize_database()
    output_path = Path(args.output) if args.output else default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    backup = {
        "metadata": {
            "app": "career-agent-os",
            "formatVersion": 1,
            "createdAt": datetime.now(UTC).isoformat(),
            "tables": TABLES,
        },
        "tables": export_tables(),
    }
    output_path.write_text(
        json.dumps(backup, indent=2 if args.pretty else None, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {sum(len(rows) for rows in backup['tables'].values())} row(s) to {output_path}")
    return 0


def default_output_path() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "deployment" / "backups" / f"career-agent-os-backup-{timestamp}.json"


def export_tables() -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}
    with get_connection() as connection:
        for table in TABLES:
            rows = connection.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(row) for row in rows]
    return data


if __name__ == "__main__":
    sys.exit(main())
