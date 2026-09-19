"""
Workflow Analyzer — Phase 10

Sends a compressed WorkflowCandidate (from Phase 9) to the LLM for
semantic interpretation, using function/tool calling to force a
response matching WorkflowInsight exactly.

Deterministic pipeline (Phases 8-9) does the compression; the LLM's
ONLY job here is semantic reasoning on already-clean data (Master
Instruction, section 11-12) — naming, classifying, and suggesting,
never re-deriving frequency/duration numbers we already computed
ourselves.
"""

from __future__ import annotations

import json

from friction_miner.llm.client import get_llm_client
from friction_miner.llm.schemas import WorkflowInsight
from friction_miner.workflow.reconstructor import WorkflowCandidate

_FUNCTION_NAME = "record_workflow_analysis"

_SYSTEM_PROMPT = """You are a workflow-analysis assistant for Friction Miner, \
a tool that detects repetitive digital work patterns.

You will receive a single reconstructed workflow: a sequence of \
(application:action) steps that a deterministic pattern-mining \
algorithm already confirmed repeats frequently, along with its \
measured frequency and duration.

Your ONLY job is semantic interpretation: name the workflow, describe \
its likely business purpose, classify its friction type(s), and \
suggest an automation approach. Do NOT invent frequency or duration \
numbers — use only the ones provided. Call the provided function with \
your analysis; do not respond with plain text."""


def _build_user_prompt(workflow: WorkflowCandidate) -> str:
    steps_str = " -> ".join(workflow.steps)
    return (
        f"Workflow steps: {steps_str}\n"
        f"Observed frequency: {workflow.frequency} occurrences\n"
        f"Average duration per occurrence: {workflow.avg_duration_seconds:.1f} seconds\n"
        f"Estimated total time across all occurrences: "
        f"{workflow.estimated_total_time_seconds / 60:.1f} minutes"
    )


def analyze_workflow(workflow: WorkflowCandidate) -> WorkflowInsight:
    """Sends one workflow candidate to the LLM and returns a validated
    WorkflowInsight. Raises if the LLM's response fails validation —
    callers must not silently accept malformed output (section 12)."""
    client, model_name = get_llm_client()

    tool_schema = {
        "type": "function",
        "function": {
            "name": _FUNCTION_NAME,
            "description": "Records the semantic analysis of a repetitive digital workflow.",
            "parameters": WorkflowInsight.model_json_schema(),
        },
    }

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(workflow)},
        ],
        tools=[tool_schema],
        tool_choice={"type": "function", "function": {"name": _FUNCTION_NAME}},
        max_tokens=1000,
        extra_body={"thinking": {"type": "disabled"}},
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise RuntimeError(
            "LLM did not return a tool call. Raw response: "
            f"{response.choices[0].message.content!r}"
        )

    arguments_json = tool_calls[0].function.arguments
    arguments = json.loads(arguments_json)

    return WorkflowInsight.model_validate(arguments)