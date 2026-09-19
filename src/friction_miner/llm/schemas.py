"""
LLM Output Schema — Phase 10

Defines the exact structure the LLM must return when interpreting a
reconstructed workflow. Matches the conceptual output shape in the
Master Instruction, section 12.

LLM output is NEVER trusted as-is (section 12: "must not automatically
be trusted"). Pydantic validation here is the enforcement mechanism —
if the model returns something outside these constraints (e.g. a
confidence of 1.5), validation fails loudly rather than silently
propagating bad data downstream.
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class FrictionType(str, Enum):
    """Closed taxonomy from Master Instruction, section 13."""

    REPETITION = "repetition"
    MANUAL_DATA_TRANSFER = "manual_data_transfer"
    CONTEXT_SWITCHING = "context_switching"
    STATUS_CHASING = "status_chasing"
    ADMINISTRATIVE_WORK = "administrative_work"
    FILE_HANDLING = "file_handling"
    APPROVAL_WAITING = "approval_waiting"
    REPETITIVE_COMMUNICATION = "repetitive_communication"
    PREDICTABLE_MANUAL_PROCESSING = "predictable_manual_processing"


class AutomationLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkflowInsight(BaseModel):
    """LLM's semantic interpretation of one reconstructed workflow."""

    workflow_name: str = Field(..., description="Short, human-readable name, 2-5 words")
    description: str = Field(..., description="1-2 sentences explaining what this workflow accomplishes")
    friction_types: List[FrictionType] = Field(..., description="One or more friction types from the fixed taxonomy")
    automation_potential: float = Field(..., ge=0.0, le=1.0, description="0.0 (not automatable) to 1.0 (fully automatable)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM's own confidence in this interpretation")
    human_judgment_required: float = Field(..., ge=0.0, le=1.0, description="Estimated share of the task needing human judgment")
    recommended_solution: str = Field(..., description="1-2 sentence suggested automation approach")
    estimated_automation_level: AutomationLevel