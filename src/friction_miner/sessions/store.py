"""
Session Store — persists ObservationSession records alongside events
and opportunities in data/friction_miner.db.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from friction_miner.sessions.models import ObservationSession, SessionStatus
from friction_miner.storage.connection import get_connection, DEFAULT_DB_PATH


def init_sessions_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                event_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_session(session: ObservationSession, db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO sessions (session_id, started_at, ended_at, event_count, status) VALUES (?, ?, ?, ?, ?)",
            (session.session_id, session.started_at.isoformat(), None, 0, session.status.value),
        )
        conn.commit()
    finally:
        conn.close()


def end_session(session_id: str, event_count: int, db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, event_count = ?, status = ? WHERE session_id = ?",
            (datetime.now().isoformat(), event_count, SessionStatus.STOPPED.value, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_sessions(db_path: Path = DEFAULT_DB_PATH) -> List[ObservationSession]:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC")
        rows = cursor.fetchall()
        results = []
        for row in rows:
            session_id, started_at, ended_at, event_count, status = row
            results.append(ObservationSession(
                session_id=session_id,
                started_at=datetime.fromisoformat(started_at),
                ended_at=datetime.fromisoformat(ended_at) if ended_at else None,
                event_count=event_count,
                status=SessionStatus(status),
            ))
        return results
    finally:
        conn.close()


def get_active_session(db_path: Path = DEFAULT_DB_PATH) -> Optional[ObservationSession]:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE status = ? ORDER BY started_at DESC LIMIT 1",
            (SessionStatus.RUNNING.value,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        session_id, started_at, ended_at, event_count, status = row
        return ObservationSession(
            session_id=session_id,
            started_at=datetime.fromisoformat(started_at),
            ended_at=datetime.fromisoformat(ended_at) if ended_at else None,
            event_count=event_count,
            status=SessionStatus(status),
        )
    finally:
        conn.close()


def count_events_for_session(session_id: str, db_path: Path = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM events WHERE session_id = ?", (session_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()