"""
Deterministic Sequence Pattern Miner — Phase 8

Finds recurring (application:event_type) sequences in the event log,
WITHOUT any LLM or ML — pure frequency counting over sliding windows,
scoped to "sessions" (bursts of activity separated by idle gaps).

Must work reliably on its own before any LLM semantic layer is
introduced (Master Instruction, section 21).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from friction_miner.events.schema import Event

DEFAULT_SESSION_GAP_SECONDS = 300  # >5 min idle => new session
DEFAULT_MIN_N = 2
DEFAULT_MAX_N = 6
DEFAULT_MIN_FREQUENCY = 3

_SHEET_TAB_RE = re.compile(r"\[sheet_tab:(\d+)\]")


def _tokenize(event: Event) -> str:
    """Reduces an event to a compact symbol for sequence matching.

    For SPA internal-tab signals (e.g. Google Sheets worksheet tabs),
    the tab identifier is folded into the token. The rest of the
    (highly variable) window title is intentionally excluded, or
    almost every window would look unique and no pattern could ever
    repeat.
    """
    base = f"{event.application}:{event.event_type.value}"

    if event.window:
        match = _SHEET_TAB_RE.search(event.window)
        if match:
            return f"{base}:sheet_tab_{match.group(1)}"

    return base


def segment_into_sessions(
    events: List[Event],
    gap_seconds: int = DEFAULT_SESSION_GAP_SECONDS,
) -> List[List[Event]]:
    """Splits a chronological event list into sessions: contiguous
    bursts of activity where no two consecutive events are more than
    `gap_seconds` apart."""
    if not events:
        return []

    sessions: List[List[Event]] = [[events[0]]]

    for prev, curr in zip(events, events[1:]):
        gap = (curr.timestamp - prev.timestamp).total_seconds()
        if gap > gap_seconds:
            sessions.append([])
        sessions[-1].append(curr)

    return sessions


@dataclass
class PatternMatch:
    sequence: Tuple[str, ...]
    frequency: int
    avg_duration_seconds: float
    example_timestamps: List[str] = field(default_factory=list)
    all_durations: List[float] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def length(self) -> int:
        return len(self.sequence)


def mine_patterns(
    events: List[Event],
    min_n: int = DEFAULT_MIN_N,
    max_n: int = DEFAULT_MAX_N,
    min_frequency: int = DEFAULT_MIN_FREQUENCY,
    session_gap_seconds: int = DEFAULT_SESSION_GAP_SECONDS,
) -> List[PatternMatch]:
    """Counts repeated n-gram sequences across sessions, for n in
    [min_n, max_n]. Returns patterns occurring >= min_frequency times,
    sorted by longest + most frequent first.
    """
    sessions = segment_into_sessions(events, gap_seconds=session_gap_seconds)
    results: List[PatternMatch] = []

    for n in range(min_n, max_n + 1):
        occurrences: dict = defaultdict(list)

        for session in sessions:
            if len(session) < n:
                continue
            tokens = [_tokenize(e) for e in session]
            for i in range(len(tokens) - n + 1):
                seq = tuple(tokens[i:i + n])
                start_ts = session[i].timestamp
                end_ts = session[i + n - 1].timestamp
                occurrences[seq].append((start_ts, end_ts))

        for seq, spans in occurrences.items():
            if len(spans) < min_frequency:
                continue
            durations = [(end - start).total_seconds() for start, end in spans]
            avg_duration = sum(durations) / len(durations)
            all_starts = [start for start, _ in spans]
            all_ends = [end for _, end in spans]
            results.append(PatternMatch(
                sequence=seq,
                frequency=len(spans),
                avg_duration_seconds=avg_duration,
                example_timestamps=[start.isoformat() for start, _ in spans[:3]],
                all_durations=durations,
                first_seen=min(all_starts),
                last_seen=max(all_ends),
            ))

    results.sort(key=lambda p: (p.length, p.frequency), reverse=True)
    return results