"""
Deterministic Sequence Pattern Miner — Phase 8

Finds recurring (application:event_type) sequences in the event log,
WITHOUT any LLM or ML — pure frequency counting over sliding windows,
scoped to "sessions" (bursts of activity separated by idle gaps).

Must work reliably on its own before any LLM semantic layer is
introduced (Master Instruction, section 21).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple

from friction_miner.events.schema import Event

DEFAULT_SESSION_GAP_SECONDS = 300  # >5 min idle => new session
DEFAULT_MIN_N = 2
DEFAULT_MAX_N = 6
DEFAULT_MIN_FREQUENCY = 3


def _tokenize(event: Event) -> str:
    """Reduces an event to a compact symbol for sequence matching."""
    return f"{event.application}:{event.event_type.value}"


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

    Note: sub-sequences of a longer frequent pattern will naturally
    also appear frequent — this is expected, not a bug. Phase 9
    collapses these into single workflows.
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
            results.append(PatternMatch(
                sequence=seq,
                frequency=len(spans),
                avg_duration_seconds=avg_duration,
                example_timestamps=[start.isoformat() for start, _ in spans[:3]],
            ))

    results.sort(key=lambda p: (p.length, p.frequency), reverse=True)
    return results