"""
Shared low-level SQLite connection helper.

All stores (events, opportunities, sessions) persist to the same
data/friction_miner.db file, so connection setup and lightweight
schema migration live in one place instead of being copy-pasted
across every store module.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/friction_miner.db")


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    """Idempotent lightweight migration: adds `column` to `table` if it
    doesn't already exist. Lets the schema evolve without deleting
    accumulated real telemetry every time a field is added."""
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
