"""
Opportunity Store — Phase 14a

Persists computed automation opportunities so the dashboard can avoid
re-calling the LLM on every page load, track user validation
decisions over time, and compute overview stats from a stable,
queryable source — rather than recomputing everything (including a
non-deterministic LLM call) on every request.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from friction_miner.opportunities.models import Opportunity, ValidationStatus

DEFAULT_DB_PATH = Path("data/friction_miner.db")


def _get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_opportunities_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                opportunity_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                steps TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                avg_duration_seconds REAL NOT NULL,
                frequency_per_week REAL NOT NULL,
                time_spent_hours_per_week REAL NOT NULL,
                predictability REAL NOT NULL,
                workflow_name TEXT NOT NULL,
                description TEXT NOT NULL,
                friction_types TEXT NOT NULL,
                automation_potential REAL NOT NULL,
                confidence REAL NOT NULL,
                human_judgment_required REAL NOT NULL,
                recommended_solution TEXT NOT NULL,
                estimated_automation_level TEXT NOT NULL,
                opportunity_score REAL NOT NULL,
                score_breakdown TEXT NOT NULL,
                validation_status TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_opportunity(opportunity: Opportunity, db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO opportunities (
                opportunity_id, created_at, steps, frequency, avg_duration_seconds,
                frequency_per_week, time_spent_hours_per_week, predictability,
                workflow_name, description, friction_types, automation_potential,
                confidence, human_judgment_required, recommended_solution,
                estimated_automation_level, opportunity_score, score_breakdown,
                validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity.opportunity_id,
                opportunity.created_at.isoformat(),
                json.dumps(opportunity.steps),
                opportunity.frequency,
                opportunity.avg_duration_seconds,
                opportunity.frequency_per_week,
                opportunity.time_spent_hours_per_week,
                opportunity.predictability,
                opportunity.workflow_name,
                opportunity.description,
                json.dumps([f.value for f in opportunity.friction_types]),
                opportunity.automation_potential,
                opportunity.confidence,
                opportunity.human_judgment_required,
                opportunity.recommended_solution,
                opportunity.estimated_automation_level.value,
                opportunity.opportunity_score,
                json.dumps(opportunity.score_breakdown),
                opportunity.validation_status.value,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_opportunities(db_path: Path = DEFAULT_DB_PATH) -> List[Opportunity]:
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM opportunities ORDER BY opportunity_score DESC")
        rows = cursor.fetchall()
        results = []
        for row in rows:
            (
                opportunity_id, created_at, steps, frequency, avg_duration_seconds,
                frequency_per_week, time_spent_hours_per_week, predictability,
                workflow_name, description, friction_types, automation_potential,
                confidence, human_judgment_required, recommended_solution,
                estimated_automation_level, opportunity_score, score_breakdown,
                validation_status,
            ) = row
            results.append(Opportunity(
                opportunity_id=opportunity_id,
                created_at=datetime.fromisoformat(created_at),
                steps=json.loads(steps),
                frequency=frequency,
                avg_duration_seconds=avg_duration_seconds,
                frequency_per_week=frequency_per_week,
                time_spent_hours_per_week=time_spent_hours_per_week,
                predictability=predictability,
                workflow_name=workflow_name,
                description=description,
                friction_types=json.loads(friction_types),
                automation_potential=automation_potential,
                confidence=confidence,
                human_judgment_required=human_judgment_required,
                recommended_solution=recommended_solution,
                estimated_automation_level=estimated_automation_level,
                opportunity_score=opportunity_score,
                score_breakdown=json.loads(score_breakdown),
                validation_status=validation_status,
            ))
        return results
    finally:
        conn.close()


def update_validation_status(
    opportunity_id: str,
    status: ValidationStatus,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "UPDATE opportunities SET validation_status = ? WHERE opportunity_id = ?",
            (status.value, opportunity_id),
        )
        conn.commit()
    finally:
        conn.close()