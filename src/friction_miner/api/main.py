"""
FastAPI Backend — Phase 14b

Thin HTTP layer over the existing pipeline modules. Contains NO
business logic itself — every endpoint just calls into modules
already built and tested in Phases 8-14a (Modularity principle,
Master Instruction section 23). This keeps the API a pure adapter:
if the underlying pipeline changes, the API barely has to.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns
from friction_miner.workflow.reconstructor import reconstruct_workflows, filter_meaningful_workflows
from friction_miner.llm.analyzer import analyze_workflow
from friction_miner.scoring.opportunity_scorer import compute_opportunity_score
from friction_miner.opportunities.models import Opportunity, ValidationStatus
from friction_miner.opportunities.store import (
    init_opportunities_db,
    save_opportunity,
    load_opportunities,
    update_validation_status,
)

APP_DB_PATH = Path("data/friction_miner.db")
SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

app = FastAPI(title="Friction Miner API")

# Dashboard runs as a local static file (opened via file:// or a
# separate dev server), so CORS must allow it. Fine for a local
# single-user prototype (Master Instruction, section 4) — would need
# tightening for any real multi-user deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_opportunities_db(APP_DB_PATH)


class ValidationUpdateRequest(BaseModel):
    status: ValidationStatus


@app.get("/api/opportunities", response_model=List[Opportunity])
def get_opportunities() -> List[Opportunity]:
    return load_opportunities(APP_DB_PATH)


@app.get("/api/overview")
def get_overview() -> dict:
    opportunities = load_opportunities(APP_DB_PATH)
    return {
        "workflows_detected": len(opportunities),
        "opportunities_detected": len(opportunities),
        "validated_opportunities": sum(
            1 for o in opportunities if o.validation_status == ValidationStatus.ACCEPTED
        ),
        "recoverable_hours_per_week": round(
            sum(o.time_spent_hours_per_week for o in opportunities), 1
        ),
    }


@app.patch("/api/opportunities/{opportunity_id}/validate")
def validate_opportunity(opportunity_id: str, body: ValidationUpdateRequest) -> dict:
    opportunities = load_opportunities(APP_DB_PATH)
    if not any(o.opportunity_id == opportunity_id for o in opportunities):
        raise HTTPException(status_code=404, detail="Opportunity not found")

    update_validation_status(opportunity_id, body.status, APP_DB_PATH)
    return {"opportunity_id": opportunity_id, "validation_status": body.status.value}


@app.post("/api/run-pipeline")
def run_pipeline() -> dict:
    """Runs the full deterministic + LLM pipeline on the synthetic
    dataset and persists results. Exists so the dashboard can trigger
    a live end-to-end run during a demo, rather than only showing
    pre-computed data."""
    events = load_events(SYNTHETIC_DB_PATH)
    patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
    workflows = filter_meaningful_workflows(reconstruct_workflows(patterns))

    saved_count = 0
    for workflow in workflows:
        insight = analyze_workflow(workflow)
        score = compute_opportunity_score(workflow, insight)
        opportunity = Opportunity.from_pipeline_output(workflow, insight, score)
        save_opportunity(opportunity, APP_DB_PATH)
        saved_count += 1

    return {"workflows_processed": len(workflows), "opportunities_saved": saved_count}