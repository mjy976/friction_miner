"""
Event Schema v0.2 — Friction Miner

Defines the canonical structure that every raw telemetry event
(from any collector: OS-level, browser, Excel, etc.) must be
normalized into before entering the pipeline.

v0.2 change: added `source` (EventSource) to distinguish real
collector data from synthetic/test data. This was added after an
incident where leftover synthetic events in the shared database
caused Pattern Mining to report phantom high-frequency patterns
that were never actually performed by the user.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Closed set of event types supported in Schema v0.1+.

    Kept intentionally small for MVP (Level 1/2 telemetry).
    New values will be added in later schema versions as
    Level 3 telemetry is introduced.
    """

    APP_SWITCH = "APP_SWITCH"
    WINDOW_FOCUS = "WINDOW_FOCUS"
    COPY = "COPY"
    PASTE = "PASTE"
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"


class EventSource(str, Enum):
    """Identifies where an event originated — critical for preventing
    synthetic/test data from contaminating real collector data."""

    REAL_COLLECTOR = "real_collector"
    SYNTHETIC = "synthetic"


class Event(BaseModel):
    """Canonical event representation for Friction Miner."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = Field(default="0.2")
    source: EventSource = Field(default=EventSource.REAL_COLLECTOR)

    timestamp: datetime
    application: str
    event_type: EventType

    window: Optional[str] = None
    duration: Optional[float] = None  # seconds

    transfer_source: Optional[str] = None       # e.g. origin app in a data-transfer action
    transfer_destination: Optional[str] = None  # e.g. destination app in a data-transfer action

    metadata: dict = Field(default_factory=dict)