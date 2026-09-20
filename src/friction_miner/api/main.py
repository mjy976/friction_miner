"""
FastAPI Backend — Phase 14b (+ collector control, dual-source pipeline)

Thin HTTP layer over the existing pipeline modules. Contains NO
business logic itself — every endpoint just calls into modules
already built and tested in Phases 8-14a.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from friction_miner.storage.db import load_events, init_db
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
from friction_miner.sessions.models import ObservationSession
from friction_miner.sessions.store import (
    init_sessions_db,
    create_session,
    end_session,
    list_sessions,
    get_active_session,
    count_events_for_session,
)

APP_DB_PATH = Path("data/friction_miner.db")
SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")
COLLECTOR_STOP_FILE = Path("data/.collector_stop_signal")
COLLECTOR_LOG_PATH = Path("data/.collector_log.txt")

app = FastAPI(title="Friction Miner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_opportunities_db(APP_DB_PATH)
init_sessions_db(APP_DB_PATH)

# In-memory handle to the currently running collector subprocess.
# Single-user, single active session at a time. Known limitation:
# resets if the API process restarts — run uvicorn WITHOUT --reload
# during real observation/demo use.
_collector_process: Optional[subprocess.Popen] = None
_collector_session_id: Optional[str] = None


class ValidationUpdateRequest(BaseModel):
    status: ValidationStatus


class RunPipelineRequest(BaseModel):
    source: str = "real"  # "real" (accumulated collector data) or "synthetic" (demo dataset)


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
def run_pipeline(body: RunPipelineRequest = RunPipelineRequest()) -> dict:
    """Runs the full deterministic + LLM pipeline.

    source="real": mines ALL accumulated real telemetry across every
    observation session to date.
    source="synthetic": always finds the same demo workflow, useful
    when real data is too sparse to have a meaningful pattern yet.
    """
    db_path = APP_DB_PATH if body.source == "real" else SYNTHETIC_DB_PATH
    init_db(db_path)
    events = load_events(db_path)

    if body.source == "real" and len(events) == 0:
        raise HTTPException(
            status_code=422,
            detail="No real activity data yet — use 'Start observing' to collect some first.",
        )

    patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
    workflows = filter_meaningful_workflows(reconstruct_workflows(patterns))

    if body.source == "real" and len(workflows) == 0:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Mined {len(events)} real events but found no repeated cross-app "
                "workflow yet. Automation opportunities need the SAME sequence to "
                "recur several times — try a longer observation session, or use "
                "the sample dataset to see the pipeline end-to-end."
            ),
        )

    saved_count = 0
    for workflow in workflows:
        insight = analyze_workflow(workflow)
        score = compute_opportunity_score(workflow, insight)
        opportunity = Opportunity.from_pipeline_output(workflow, insight, score)
        save_opportunity(opportunity, APP_DB_PATH)
        saved_count += 1

    return {
        "source": body.source,
        "events_scanned": len(events),
        "workflows_processed": len(workflows),
        "opportunities_saved": saved_count,
    }


@app.get("/api/collector/status")
def collector_status() -> dict:
    global _collector_process
    running = _collector_process is not None and _collector_process.poll() is None
    if not running:
        _collector_process = None

    active = get_active_session(APP_DB_PATH) if running else None
    return {
        "running": running,
        "session_id": active.session_id if active else None,
        "started_at": active.started_at.isoformat() if active else None,
    }


@app.post("/api/collector/start")
def collector_start() -> dict:
    global _collector_process, _collector_session_id

    if _collector_process is not None and _collector_process.poll() is None:
        raise HTTPException(status_code=409, detail="Collector is already running")

    if COLLECTOR_STOP_FILE.exists():
        COLLECTOR_STOP_FILE.unlink()

    session = ObservationSession(session_id=str(uuid.uuid4()))
    create_session(session, APP_DB_PATH)

    log_file = open(COLLECTOR_LOG_PATH, "w", encoding="utf-8")
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    _collector_process = subprocess.Popen(
        [sys.executable, "-m", "friction_miner.collector.main_collector",
         session.session_id, str(COLLECTOR_STOP_FILE)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    log_file.close()
    _collector_session_id = session.session_id

    return {"session_id": session.session_id, "started_at": session.started_at.isoformat()}


@app.post("/api/collector/stop")
def collector_stop() -> dict:
    global _collector_process, _collector_session_id

    if _collector_process is None or _collector_process.poll() is not None:
        raise HTTPException(status_code=409, detail="Collector is not running")

    COLLECTOR_STOP_FILE.touch()

    try:
        _collector_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _collector_process.terminate()

    event_count = count_events_for_session(_collector_session_id, APP_DB_PATH)
    end_session(_collector_session_id, event_count, APP_DB_PATH)

    stopped_session_id = _collector_session_id
    _collector_process = None
    _collector_session_id = None

    return {"session_id": stopped_session_id, "event_count": event_count}


@app.get("/api/sessions", response_model=List[ObservationSession])
def get_sessions() -> List[ObservationSession]:
    return list_sessions(APP_DB_PATH)