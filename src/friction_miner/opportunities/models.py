"""
Opportunity record — Phase 14a

Bundles one fully-processed automation opportunity: the deterministic
workflow evidence (Phase 8-9), the LLM's semantic interpretation
(Phase 10), and the explainable score (Phase 12) into a single
persisted record, plus a validation status the user sets in the
dashboard (Master Instruction, section 15).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field

from friction_miner.llm.schemas import FrictionType, AutomationLevel, WorkflowInsight
from friction_miner.workflow.reconstructor import WorkflowCandidate
from friction_miner.scoring.opportunity_scorer import OpportunityScore


class ValidationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class Opportunity(BaseModel):
    opportunity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)

    # Deterministic evidence (Phase 8-9)
    steps: List[str]
    frequency: int
    avg_duration_seconds: float
    frequency_per_week: float
    time_spent_hours_per_week: float
    predictability: float

    # LLM semantic interpretation (Phase 10)
    workflow_name: str
    description: str
    friction_types: List[FrictionType]
    automation_potential: float
    confidence: float
    human_judgment_required: float
    recommended_solution: str
    estimated_automation_level: AutomationLevel

    # Explainable score (Phase 12)
    opportunity_score: float
    score_breakdown: Dict[str, Dict[str, float]]

    # User validation (section 15) — defaults to pending until reviewed
    validation_status: ValidationStatus = ValidationStatus.PENDING

    @classmethod
    def from_pipeline_output(
        cls,
        workflow: WorkflowCandidate,
        insight: WorkflowInsight,
        score: OpportunityScore,
    ) -> "Opportunity":
        """Builds an Opportunity by combining the three pipeline
        stages' outputs — keeps assembly logic in one place instead
        of duplicating it wherever the pipeline is run."""
        return cls(
            steps=list(workflow.steps),
            frequency=workflow.frequency,
            avg_duration_seconds=workflow.avg_duration_seconds,
            frequency_per_week=score.frequency_per_week,
            time_spent_hours_per_week=score.time_spent_hours_per_week,
            predictability=score.predictability,
            workflow_name=insight.workflow_name,
            description=insight.description,
            friction_types=insight.friction_types,
            automation_potential=insight.automation_potential,
            confidence=insight.confidence,
            human_judgment_required=insight.human_judgment_required,
            recommended_solution=insight.recommended_solution,
            estimated_automation_level=insight.estimated_automation_level,
            opportunity_score=score.total_score,
            score_breakdown=score.breakdown,
        )