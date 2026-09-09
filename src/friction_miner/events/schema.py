"""
Event Schema v0.1 — Friction Miner

Defines the canonical structure that every raw telemetry event
(from any collector: OS-level, browser, Excel, etc.) must be
normalized into before entering the pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Closed set of event types supported in Schema v0.1.

    Kept intentionally small for MVP (Level 1 telemetry).
    New values will be added in later schema versions as
    Level 2/3 telemetry is introduced.
    """

    APP_SWITCH = "APP_SWITCH"
    WINDOW_FOCUS = "WINDOW_FOCUS"
    COPY = "COPY"
    PASTE = "PASTE"
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"


class Event(BaseModel):
    """Canonical event representation for Friction Miner."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = Field(default="0.1")

    timestamp: datetime
    application: str
    event_type: EventType

    window: Optional[str] = None
    duration: Optional[float] = None  # seconds

    source: Optional[str] = None
    destination: Optional[str] = None

    metadata: dict = Field(default_factory=dict)