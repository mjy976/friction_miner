"""
Workflow Reconstruction — Phase 9

Collapses the many overlapping n-gram patterns produced by
sequence_miner.mine_patterns() into a small set of canonical
"workflow candidates" — the maximal repeated sequences, with
shorter sub-sequences folded in as supporting evidence rather
than reported as separate findings.

This MUST happen before any LLM involvement (Master Instruction,
section 11): raw/overlapping patterns are compressed into a clean
structured representation first, so the LLM interprets meaning,
not redundant fragments of the same behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from friction_miner.mining.sequence_miner import PatternMatch

DEFAULT_FREQUENCY_TOLERANCE = 0.2


@dataclass
class WorkflowCandidate:
    """A single reconstructed workflow: the longest observed sequence
    that repeats, with shorter matching sub-sequences absorbed as
    evidence rather than listed separately."""

    steps: Tuple[str, ...]
    frequency: int
    avg_duration_seconds: float
    example_timestamps: List[str] = field(default_factory=list)
    absorbed_subpatterns: int = 0
    all_durations: List[float] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def estimated_total_time_seconds(self) -> float:
        return self.frequency * self.avg_duration_seconds

    @property
    def observed_span_days(self) -> float:
        """Days between the first and last observed occurrence.
        Floored at 1.0 — with a short observation window (e.g. a few
        minutes of test data), extrapolating to a weekly rate without
        this floor would produce wildly unrealistic numbers. This is
        a known limitation: scores are most meaningful once real data
        spans multiple days/weeks, not a single short session."""
        if self.first_seen is None or self.last_seen is None:
            return 1.0
        days = (self.last_seen - self.first_seen).total_seconds() / 86400
        return max(days, 1.0)


def _is_contiguous_subsequence(shorter: Tuple[str, ...], longer: Tuple[str, ...]) -> bool:
    n, m = len(shorter), len(longer)
    if n > m:
        return False
    return any(longer[i:i + n] == shorter for i in range(m - n + 1))


def reconstruct_workflows(
    patterns: List[PatternMatch],
    frequency_tolerance: float = DEFAULT_FREQUENCY_TOLERANCE,
) -> List[WorkflowCandidate]:
    ordered = sorted(patterns, key=lambda p: (p.length, p.frequency), reverse=True)
    accepted: List[WorkflowCandidate] = []

    for pattern in ordered:
        absorbed = False

        for candidate in accepted:
            if not _is_contiguous_subsequence(pattern.sequence, candidate.steps):
                continue

            lower_bound = candidate.frequency * (1 - frequency_tolerance)
            if lower_bound <= pattern.frequency <= candidate.frequency:
                candidate.absorbed_subpatterns += 1
                absorbed = True
                break

        if not absorbed:
            accepted.append(WorkflowCandidate(
                steps=pattern.sequence,
                frequency=pattern.frequency,
                avg_duration_seconds=pattern.avg_duration_seconds,
                example_timestamps=list(pattern.example_timestamps),
                all_durations=list(pattern.all_durations),
                first_seen=pattern.first_seen,
                last_seen=pattern.last_seen,
            ))

    accepted.sort(key=lambda w: w.frequency * w.step_count, reverse=True)
    return accepted


def filter_meaningful_workflows(
    workflows: List[WorkflowCandidate],
    min_distinct_applications: int = 2,
) -> List[WorkflowCandidate]:
    """Drops workflow candidates confined to a single application."""
    result = []
    for w in workflows:
        distinct_apps = {step.split(":", 1)[0] for step in w.steps}
        if len(distinct_apps) >= min_distinct_applications:
            result.append(w)
    return result