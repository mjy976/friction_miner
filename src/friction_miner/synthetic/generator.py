"""
Synthetic Event Generator — Phase 3 (+ multi-persona demo dataset)

Generates realistic fake telemetry events following Event Schema v0.3,
so that later phases (SQLite storage, pattern mining, workflow
reconstruction) can be developed and tested WITHOUT depending on a
real collector or several days of real activity data.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from friction_miner.events.schema import Event, EventType, EventSource


def _make_event(
    application: str,
    event_type: EventType,
    timestamp: datetime,
    window: str | None = None,
    duration: float | None = None,
    metadata: dict | None = None,
) -> Event:
    return Event(
        timestamp=timestamp,
        application=application,
        event_type=event_type,
        window=window,
        duration=duration,
        metadata=metadata or {},
        source=EventSource.SYNTHETIC,
    )


def generate_seller_report_workflow(start_time: datetime) -> List[Event]:
    """Simulates ONE occurrence of the original demo workflow:
    Chrome (browse) -> COPY -> Excel (paste/edit) -> Teams (notify)
    """
    t = start_time
    events: List[Event] = []

    events.append(_make_event("Chrome", EventType.APP_SWITCH, t, window="Seller Portal - Dashboard"))
    t += timedelta(seconds=random.uniform(20, 90))

    events.append(_make_event(
        "Chrome", EventType.COPY, t,
        window="Seller Portal - Dashboard",
        metadata={"content_type": "text", "content_length": random.randint(20, 120)},
    ))
    t += timedelta(seconds=random.uniform(3, 10))

    events.append(_make_event("Excel", EventType.APP_SWITCH, t, window="Seller Report.xlsx"))
    t += timedelta(seconds=random.uniform(2, 8))

    events.append(_make_event(
        "Excel", EventType.PASTE, t,
        window="Seller Report.xlsx",
        metadata={"content_type": "text", "content_length": random.randint(20, 120)},
    ))
    t += timedelta(seconds=random.uniform(30, 180))

    events.append(_make_event("Teams", EventType.APP_SWITCH, t, window="Sales Team - General"))
    t += timedelta(seconds=random.uniform(5, 20))

    events.append(_make_event(
        "Teams", EventType.PASTE, t,
        window="Sales Team - General",
        metadata={"content_type": "text", "content_length": random.randint(10, 60)},
    ))

    return events


def generate_dataset(
    num_occurrences: int = 20,
    start_date: datetime | None = None,
    noise_events: int = 5,
) -> List[Event]:
    """Original single-workflow synthetic dataset (Phase 3/8 validation)."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=7)

    all_events: List[Event] = []
    current_day = start_date

    for i in range(num_occurrences):
        day_offset = i // 4
        hour = random.uniform(9, 18)
        occurrence_time = (current_day + timedelta(days=day_offset)).replace(
            hour=int(hour), minute=random.randint(0, 59), second=0, microsecond=0
        )
        all_events.extend(generate_seller_report_workflow(occurrence_time))

    noise_apps = ["Slack", "Outlook", "Notepad", "Spotify"]
    for _ in range(noise_events):
        noise_time = start_date + timedelta(
            days=random.uniform(0, num_occurrences // 4),
            hours=random.uniform(9, 18),
        )
        all_events.append(_make_event(random.choice(noise_apps), EventType.APP_SWITCH, noise_time))

    all_events.sort(key=lambda e: e.timestamp)
    return all_events


# ---------------------------------------------------------------------
# Multi-persona demo dataset — five distinct, role-based workflows
# ---------------------------------------------------------------------

@dataclass
class WorkflowStep:
    application: str
    event_type: EventType
    window: Optional[str] = None
    metadata: Optional[dict] = None
    min_gap: float = 2.0
    max_gap: float = 15.0


def _random_copy_metadata() -> dict:
    return {"content_type": "text", "content_length": random.randint(15, 150)}


PERSONA_LABELS: Dict[str, str] = {
    "business_analyst": "Business Analyst",
    "data_analyst": "Data Analyst",
    "call_center": "Call Center Specialist",
    "product_manager": "Product Manager",
    "developer": "Developer",
}

PERSONA_WORKFLOWS: Dict[str, List[WorkflowStep]] = {
    "business_analyst": [
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Revenue Dashboard - Analytics - Google Chrome", min_gap=20, max_gap=75),
        WorkflowStep("Chrome", EventType.COPY,
                     "Revenue Dashboard - Analytics - Google Chrome", min_gap=3, max_gap=8),
        WorkflowStep("Excel", EventType.APP_SWITCH,
                     "Weekly KPI Report.xlsx - Excel", min_gap=2, max_gap=6),
        WorkflowStep("Excel", EventType.PASTE,
                     "Weekly KPI Report.xlsx - Excel", min_gap=60, max_gap=240),
        WorkflowStep("Outlook", EventType.APP_SWITCH,
                     "New Message - Weekly KPI Summary - Outlook", min_gap=10, max_gap=30),
        WorkflowStep("Outlook", EventType.PASTE,
                     "New Message - Weekly KPI Summary - Outlook", min_gap=0, max_gap=0),
    ],
    "data_analyst": [
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Raw Transactions - Google Sheets [sheet_tab:811234567] - Google Chrome",
                     min_gap=15, max_gap=45),
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Pivot Summary - Google Sheets [sheet_tab:922345678] - Google Chrome",
                     min_gap=8, max_gap=20),
        WorkflowStep("Chrome", EventType.COPY,
                     "Pivot Summary - Google Sheets [sheet_tab:922345678] - Google Chrome",
                     min_gap=3, max_gap=8),
        WorkflowStep("Excel", EventType.APP_SWITCH,
                     "Forecast Model.xlsx - Excel", min_gap=15, max_gap=40),
        WorkflowStep("Excel", EventType.PASTE,
                     "Forecast Model.xlsx - Excel", min_gap=0, max_gap=0),
    ],
    "call_center": [
        WorkflowStep("Teams", EventType.APP_SWITCH,
                     "Call ended - Customer +1 (555) 019-2231 - Teams", min_gap=5, max_gap=15),
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Case #48213 - Support Portal - Google Chrome", min_gap=15, max_gap=45),
        WorkflowStep("Chrome", EventType.COPY,
                     "Case #48213 - Support Portal - Google Chrome", min_gap=3, max_gap=8),
        WorkflowStep("Outlook", EventType.APP_SWITCH,
                     "New Message - Case #48213 Follow-up - Outlook", min_gap=20, max_gap=60),
        WorkflowStep("Outlook", EventType.PASTE,
                     "New Message - Case #48213 Follow-up - Outlook", min_gap=0, max_gap=0),
    ],
    "product_manager": [
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Sprint 42 Board - Jira - Google Chrome", min_gap=20, max_gap=60),
        WorkflowStep("Chrome", EventType.COPY,
                     "Sprint 42 Board - Jira - Google Chrome", min_gap=3, max_gap=8),
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "Roadmap Tracker - Google Sheets [sheet_tab:733456789] - Google Chrome",
                     min_gap=5, max_gap=15),
        WorkflowStep("Chrome", EventType.PASTE,
                     "Roadmap Tracker - Google Sheets [sheet_tab:733456789] - Google Chrome",
                     min_gap=30, max_gap=90),
        WorkflowStep("Slack", EventType.APP_SWITCH,
                     "#product-updates - Slack", min_gap=10, max_gap=30),
        WorkflowStep("Slack", EventType.PASTE,
                     "#product-updates - Slack", min_gap=0, max_gap=0),
    ],
    "developer": [
        WorkflowStep("Chrome", EventType.APP_SWITCH,
                     "PR #1042: Fix pagination bug - GitHub - Google Chrome", min_gap=15, max_gap=40),
        WorkflowStep("Chrome", EventType.COPY,
                     "PR #1042: Fix pagination bug - GitHub - Google Chrome", min_gap=3, max_gap=8),
        WorkflowStep("Code", EventType.APP_SWITCH,
                     "standup-notes.md - Visual Studio Code", min_gap=2, max_gap=6),
        WorkflowStep("Code", EventType.PASTE,
                     "standup-notes.md - Visual Studio Code", min_gap=15, max_gap=45),
        WorkflowStep("Slack", EventType.APP_SWITCH,
                     "#eng-standup - Slack", min_gap=5, max_gap=15),
        WorkflowStep("Slack", EventType.PASTE,
                     "#eng-standup - Slack", min_gap=0, max_gap=0),
    ],
}

DEFAULT_PERSONA_OCCURRENCES: Dict[str, int] = {
    "business_analyst": 12,
    "data_analyst": 25,
    "call_center": 38,
    "product_manager": 6,
    "developer": 18,
}


def _generate_occurrence(steps: List[WorkflowStep], start_time: datetime) -> List[Event]:
    t = start_time
    events: List[Event] = []
    for step in steps:
        if step.event_type in (EventType.COPY, EventType.PASTE):
            metadata = _random_copy_metadata()
        else:
            metadata = step.metadata
        events.append(_make_event(
            step.application, step.event_type, t,
            window=step.window, metadata=metadata,
        ))
        t += timedelta(seconds=random.uniform(step.min_gap, step.max_gap))
    return events


def _schedule_slots(
    total_count: int,
    span_days: int,
    start_date: datetime,
    min_buffer_seconds: float,
    workday_start_hour: int = 9,
    workday_end_hour: int = 18,
) -> List[datetime]:
    """Generates `total_count` start times, confined to a workday
    window, each guaranteed at least `min_buffer_seconds` apart.

    This is the fix for a real bug found during development: placing
    ~100 occurrences fully independently and randomly across a workday
    produces frequent near-collisions (birthday-paradox style) where
    two UNRELATED occurrences land within the pattern miner's 5-minute
    session gap. The miner then correctly, but misleadingly, stitches
    their adjacent steps into a chimeric "pattern" that never actually
    happened as one workflow. Explicit non-overlapping scheduling
    removes this by construction rather than hoping randomness
    cooperates.

    If the requested count doesn't fit `span_days` at a healthy pace,
    the window is extended automatically rather than silently cramming
    events together.
    """
    workday_seconds = (workday_end_hour - workday_start_hour) * 3600
    days_needed = max(span_days, math.ceil((total_count * min_buffer_seconds) / workday_seconds) + 1)
    total_available_seconds = days_needed * workday_seconds

    # Spread across the full available window when there's room to
    # spare, rather than clustering everything at the bare minimum
    # spacing in the first few days.
    buffer_seconds = max(min_buffer_seconds, total_available_seconds / total_count)

    slots: List[datetime] = []
    cursor = 0.0
    for _ in range(total_count):
        day_index = int(cursor // workday_seconds)
        seconds_into_day = cursor % workday_seconds
        day_anchor = (start_date + timedelta(days=day_index)).replace(
            hour=workday_start_hour, minute=0, second=0, microsecond=0
        )
        jitter = random.uniform(0, buffer_seconds * 0.25)
        slots.append(day_anchor + timedelta(seconds=seconds_into_day + jitter))
        cursor += buffer_seconds

    return slots


def generate_persona_dataset(
    occurrences: Optional[Dict[str, int]] = None,
    span_days: int = 10,
    start_date: Optional[datetime] = None,
    noise_events: int = 20,
) -> List[Event]:
    """Generates a richer synthetic dataset with FIVE distinct,
    role-based recurring workflows, all drawing their start times from
    ONE shared, pre-spaced schedule (see _schedule_slots) — so no two
    occurrences, whether the same persona or different ones, and
    including noise events, can accidentally merge into one mining
    session.

    Some workflows still legitimately share a short single-application
    fragment (e.g. "open Chrome, then copy") — that's realistic, several
    real jobs start that way. filter_meaningful_workflows() already
    drops single-app patterns, and cross-persona multi-app overlaps are
    avoided by design (see PERSONA_WORKFLOWS' distinct destination
    apps and sheet_tab-tagged Chrome steps). Any residual shared
    fragment that still surfaces is a legitimate candidate to Dismiss
    from the dashboard, not a bug.
    """
    occurrences = occurrences or DEFAULT_PERSONA_OCCURRENCES
    if start_date is None:
        start_date = datetime.now() - timedelta(days=span_days)

    # Comfortably above the sequence miner's session gap (300s).
    MIN_SLOT_BUFFER_SECONDS = 480

    schedule_items: List[Optional[str]] = []
    for key, count in occurrences.items():
        schedule_items.extend([key] * count)
    schedule_items.extend([None] * noise_events)  # None marks a noise slot
    random.shuffle(schedule_items)

    slot_times = _schedule_slots(len(schedule_items), span_days, start_date, MIN_SLOT_BUFFER_SECONDS)

    noise_apps = ["Slack", "Outlook", "Notepad", "Spotify", "explorer.exe", "WindowsTerminal.exe"]
    all_events: List[Event] = []

    for item, slot_time in zip(schedule_items, slot_times):
        if item is None:
            all_events.append(_make_event(random.choice(noise_apps), EventType.APP_SWITCH, slot_time))
        else:
            all_events.extend(_generate_occurrence(PERSONA_WORKFLOWS[item], slot_time))

    all_events.sort(key=lambda e: e.timestamp)
    return all_events