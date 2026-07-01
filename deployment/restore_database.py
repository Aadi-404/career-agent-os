import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = ROOT / "ai-service"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_SERVICE_DIR))

from app.db import get_connection, initialize_database  # noqa: E402
from deployment.backup_database import TABLES  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore Career Agent OS PostgreSQL data from a JSON backup.")
    parser.add_argument("backup", help="Path to a JSON backup created by deployment/backup_database.py.")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive restore.")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Refusing to restore without --yes. This replaces rows in application tables.")

    backup_path = Path(args.backup)
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise SystemExit("Invalid backup: missing tables object.")

    initialize_database()
    restored = restore_tables(tables)
    print(f"Restored {restored} row(s) from {backup_path}")
    return 0


def restore_tables(tables: dict[str, Any]) -> int:
    restored = 0
    with get_connection() as connection:
        for table in reversed(TABLES):
            connection.execute(f"DELETE FROM {quote_identifier(table)}")
        for table in TABLES:
            rows = tables.get(table, [])
            if not isinstance(rows, list):
                raise SystemExit(f"Invalid backup: table {table} is not a list.")
            for row in rows:
                if not isinstance(row, dict):
                    raise SystemExit(f"Invalid backup: table {table} contains a non-object row.")
                insert_row(connection, table, row)
                restored += 1
    return restored


def insert_row(connection, table: str, row: dict[str, Any]) -> None:
    if not row:
        return
    columns = list(row.keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    values = tuple(row[column] for column in columns)
    connection.execute(
        f"INSERT INTO {quote_identifier(table)} ({column_sql}) VALUES ({placeholders})",
        values,
    )


def quote_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise SystemExit(f"Unsafe SQL identifier in backup: {value}")
    return f'"{value}"'


if __name__ == "__main__":
    sys.exit(main())
