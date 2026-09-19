"""
Synthetic Event Generator — Phase 3

Generates realistic fake telemetry events following Event Schema v0.1,
so that later phases (SQLite storage, pattern mining, workflow
reconstruction) can be developed and tested WITHOUT depending on a
real collector or several days of real activity data.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

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
    """Simulates ONE occurrence of the target demo workflow:

    Chrome (browse) -> COPY -> Excel (paste/edit) -> Teams (notify)

    Returns events in chronological order with small realistic gaps.
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
    """Generates a full synthetic dataset:

    - `num_occurrences` repetitions of the target workflow, spread
      across working hours over several days.
    - A few random unrelated "noise" events, so pattern detection
      later has to actually find the signal, not just return everything.
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=7)

    all_events: List[Event] = []
    current_day = start_date

    for i in range(num_occurrences):
        # Spread occurrences across working hours (9am-6pm) over several days
        day_offset = i // 4  # ~4 occurrences per day
        hour = random.uniform(9, 18)
        occurrence_time = (current_day + timedelta(days=day_offset)).replace(
            hour=int(hour), minute=random.randint(0, 59), second=0, microsecond=0
        )
        all_events.extend(generate_seller_report_workflow(occurrence_time))

    # Add some random noise events (unrelated app switches)
    noise_apps = ["Slack", "Outlook", "Notepad", "Spotify"]
    for _ in range(noise_events):
        noise_time = start_date + timedelta(
            days=random.uniform(0, num_occurrences // 4),
            hours=random.uniform(9, 18),
        )
        all_events.append(_make_event(
            random.choice(noise_apps), EventType.APP_SWITCH, noise_time
        ))

    all_events.sort(key=lambda e: e.timestamp)
    return all_events