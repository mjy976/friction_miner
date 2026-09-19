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
from typing import List, Tuple

from friction_miner.mining.sequence_miner import PatternMatch

# A sub-pattern is considered "the same workflow, seen at a shorter
# window" if its frequency is within this fraction of its parent's
# frequency. A sub-pattern occurring MUCH more often than any parent
# is kept as its own independent workflow candidate instead.
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

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def estimated_total_time_seconds(self) -> float:
        """Rough total time spent on this workflow across all observed
        occurrences (frequency x average duration per occurrence)."""
        return self.frequency * self.avg_duration_seconds


def _is_contiguous_subsequence(shorter: Tuple[str, ...], longer: Tuple[str, ...]) -> bool:
    """True if `shorter` appears as a contiguous slice of `longer`."""
    n, m = len(shorter), len(longer)
    if n > m:
        return False
    return any(longer[i:i + n] == shorter for i in range(m - n + 1))


def reconstruct_workflows(
    patterns: List[PatternMatch],
    frequency_tolerance: float = DEFAULT_FREQUENCY_TOLERANCE,
) -> List[WorkflowCandidate]:
    """Collapses overlapping n-gram patterns into canonical workflow
    candidates. See module docstring for the absorption rule."""

    # Longest first, then most frequent — always anchor on the most
    # complete picture of a workflow before considering its fragments.
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
            ))

    # Show the most impactful workflows first (frequency x step count
    # is a simple proxy for "how much repeated activity this explains").
    accepted.sort(key=lambda w: w.frequency * w.step_count, reverse=True)
    return accepted

def filter_meaningful_workflows(
    workflows: List[WorkflowCandidate],
    min_distinct_applications: int = 2,
) -> List[WorkflowCandidate]:
    """Drops workflow candidates confined to a single application.

    Single-app repeated navigation (e.g. clicking through folders in
    File Explorer) tokenizes identically regardless of which folder
    was visited, producing "patterns" that are statistical artifacts
    of coarse tokenization, not real cross-app friction. The product
    hypothesis (manual data transfer BETWEEN applications) requires
    at least 2 distinct applications to be a valid candidate.
    """
    result = []
    for w in workflows:
        distinct_apps = {step.split(":", 1)[0] for step in w.steps}
        if len(distinct_apps) >= min_distinct_applications:
            result.append(w)
    return result