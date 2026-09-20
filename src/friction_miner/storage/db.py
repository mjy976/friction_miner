"""
SQLite Event Store — Phase 4 (+ session_id in v0.3)

Responsible ONLY for persisting and retrieving Event objects.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from friction_miner.events.schema import Event, EventType, EventSource
from friction_miner.storage.connection import get_connection, ensure_column, DEFAULT_DB_PATH


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                source TEXT NOT NULL,
                session_id TEXT,
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
        # Idempotent migration for databases created before session_id existed.
        ensure_column(conn, "events", "session_id", "TEXT")
        conn.commit()
    finally:
        conn.close()


def save_events(events: List[Event], db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO events (
                event_id, schema_version, source, session_id, timestamp, application,
                event_type, window, duration, transfer_source, transfer_destination, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.event_id,
                    e.schema_version,
                    e.source.value,
                    e.session_id,
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
    session_id: Optional[str] = None,
) -> List[Event]:
    conn = get_connection(db_path)
    try:
        query = (
            "SELECT event_id, schema_version, source, session_id, timestamp, application, "
            "event_type, window, duration, transfer_source, transfer_destination, metadata "
            "FROM events"
        )
        conditions = []
        params: list = []

        if start is not None:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end is not None:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())
        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        events = []
        for row in rows:
            (
                event_id, schema_version, source, session_id_val, timestamp, application,
                event_type, window, duration, transfer_source, transfer_destination, metadata,
            ) = row
            events.append(
                Event(
                    event_id=event_id,
                    schema_version=schema_version,
                    source=EventSource(source),
                    session_id=session_id_val,
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
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]
    finally:
        conn.close()