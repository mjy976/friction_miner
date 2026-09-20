"""
Observation Session — the persistent "bank" of every Start→Stop
observation cycle. Each real Event is tagged with the session_id of
the run that captured it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"


class ObservationSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    event_count: int = 0
    status: SessionStatus = SessionStatus.RUNNING