"""
SQLite Event Store — Phase 4

Responsible ONLY for persisting and retrieving Event objects.
Does not know or care where events came from (synthetic generator,
real collector, etc.) — that separation is intentional (Modularity
principle).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from friction_miner.events.schema import Event, EventType, EventSource

DEFAULT_DB_PATH = Path("data/friction_miner.db")


def _get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                application TEXT NOT NULL,
                event_type TEXT NOT NULL,
                window TEXT,
                duration REAL,
                transfer_source TEXT,
                transfer_destination TEXT,
                metadata TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_events(events: List[Event], db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = _get_connection(db_path)
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO events (
                event_id, schema_version, source, timestamp, application,
                event_type, window, duration, transfer_source, transfer_destination, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.event_id,
                    e.schema_version,
                    e.source.value,
                    e.timestamp.isoformat(),
                    e.application,
                    e.event_type.value,
                    e.window,
                    e.duration,
                    e.transfer_source,
                    e.transfer_destination,
                    json.dumps(e.metadata),
                )
                for e in events
            ],
        )
        conn.commit()
    finally:
        conn.close()


def load_events(
    db_path: Path = DEFAULT_DB_PATH,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Event]:
    conn = _get_connection(db_path)
    try:
        query = "SELECT * FROM events"
        conditions = []
        params: list = []

        if start is not None:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end is not None:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        events = []
        for row in rows:
            (
                event_id, schema_version, source, timestamp, application,
                event_type, window, duration, transfer_source, transfer_destination, metadata,
            ) = row
            events.append(
                Event(
                    event_id=event_id,
                    schema_version=schema_version,
                    source=EventSource(source),
                    timestamp=datetime.fromisoformat(timestamp),
                    application=application,
                    event_type=EventType(event_type),
                    window=window,
                    duration=duration,
                    transfer_source=transfer_source,
                    transfer_destination=transfer_destination,
                    metadata=json.loads(metadata),
                )
            )
        return events
    finally:
        conn.close()


def count_events(db_path: Path = DEFAULT_DB_PATH) -> int:
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]
    finally:
        conn.close()