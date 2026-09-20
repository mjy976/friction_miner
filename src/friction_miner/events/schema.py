"""
Event Schema v0.3 — Friction Miner

v0.3 change: added `session_id`, tying every event to the observation
session (Start→Stop cycle) that captured it. This is what makes the
"bank" of past observation sessions possible — every session's
telemetry stays queryable on its own, forever, instead of collapsing
into one undifferentiated pile of events.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    APP_SWITCH = "APP_SWITCH"
    WINDOW_FOCUS = "WINDOW_FOCUS"
    COPY = "COPY"
    PASTE = "PASTE"
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"


class EventSource(str, Enum):
    REAL_COLLECTOR = "real_collector"
    SYNTHETIC = "synthetic"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = Field(default="0.3")
    source: EventSource = Field(default=EventSource.REAL_COLLECTOR)
    session_id: Optional[str] = None

    timestamp: datetime
    application: str
    event_type: EventType

    window: Optional[str] = None
    duration: Optional[float] = None

    transfer_source: Optional[str] = None
    transfer_destination: Optional[str] = None

    metadata: dict = Field(default_factory=dict)