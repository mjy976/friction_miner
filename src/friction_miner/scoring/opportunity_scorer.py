"""
Opportunity Scoring — Phase 12

Deterministic, explainable scoring of a reconstructed+interpreted
workflow's automation opportunity. Master Instruction section 14 is
explicit: the LLM must not decide which opportunity matters most —
scoring is a fixed, auditable formula over measured + LLM-provided
inputs, never a number the LLM invents on its own.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List

from friction_miner.workflow.reconstructor import WorkflowCandidate
from friction_miner.llm.schemas import WorkflowInsight

# Normalization caps: values at/above these are treated as "maximum
# impact" (normalized to 1.0). Reasonable starting assumptions for one
# knowledge worker's repetitive workflow — tune once real usage data
# accumulates.
FREQUENCY_CAP_PER_WEEK = 30.0
TIME_CAP_HOURS_PER_WEEK = 5.0

WEIGHTS = {
    "frequency": 0.25,
    "time_spent": 0.25,
    "predictability": 0.15,
    "automation_potential": 0.25,
    "low_human_judgment": 0.10,
}


@dataclass
class OpportunityScore:
    frequency_per_week: float
    time_spent_hours_per_week: float
    predictability: float
    automation_potential: float
    human_judgment_required: float
    total_score: float
    breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)


def _compute_predictability(durations: List[float]) -> float:
    """1.0 = every occurrence took almost the same time (consistent,
    safe to automate). 0.0 = wildly inconsistent duration. Based on
    coefficient of variation (stdev / mean), clipped to [0, 1]."""
    if len(durations) < 2:
        return 0.5  # not enough samples to judge consistency either way
    mean = statistics.mean(durations)
    if mean == 0:
        return 1.0
    coefficient_of_variation = statistics.pstdev(durations) / mean
    return max(0.0, 1.0 - min(coefficient_of_variation, 1.0))


def compute_opportunity_score(
    workflow: WorkflowCandidate,
    insight: WorkflowInsight,
) -> OpportunityScore:
    """Combines deterministic telemetry (frequency, duration,
    consistency) with the LLM's semantic judgment (automation
    potential, human judgment required) into one explainable score."""
    observed_days = workflow.observed_span_days
    frequency_per_week = workflow.frequency / observed_days * 7
    time_spent_hours_per_week = (
        workflow.frequency * workflow.avg_duration_seconds / 3600
    ) / observed_days * 7

    predictability = _compute_predictability(workflow.all_durations)

    components = {
        "frequency": (
            frequency_per_week,
            min(frequency_per_week / FREQUENCY_CAP_PER_WEEK, 1.0),
        ),
        "time_spent": (
            time_spent_hours_per_week,
            min(time_spent_hours_per_week / TIME_CAP_HOURS_PER_WEEK, 1.0),
        ),
        "predictability": (predictability, predictability),
        "automation_potential": (
            insight.automation_potential, insight.automation_potential,
        ),
        "low_human_judgment": (
            insight.human_judgment_required,
            1.0 - insight.human_judgment_required,
        ),
    }

    breakdown: Dict[str, Dict[str, float]] = {}
    total = 0.0
    for name, (raw, normalized) in components.items():
        weight = WEIGHTS[name]
        contribution = normalized * weight * 100
        breakdown[name] = {
            "raw": raw,
            "normalized": normalized,
            "weight": weight,
            "contribution": contribution,
        }
        total += contribution

    return OpportunityScore(
        frequency_per_week=frequency_per_week,
        time_spent_hours_per_week=time_spent_hours_per_week,
        predictability=predictability,
        automation_potential=insight.automation_potential,
        human_judgment_required=insight.human_judgment_required,
        total_score=round(total, 1),
        breakdown=breakdown,
    )