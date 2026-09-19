from pathlib import Path

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns
from friction_miner.workflow.reconstructor import reconstruct_workflows, filter_meaningful_workflows
from friction_miner.llm.analyzer import analyze_workflow
from friction_miner.scoring.opportunity_scorer import compute_opportunity_score
from friction_miner.opportunities.models import Opportunity
from friction_miner.opportunities.store import init_opportunities_db, save_opportunity, load_opportunities

SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")
APP_DB_PATH = Path("data/friction_miner.db")  # opportunities table lives alongside real events

init_opportunities_db(APP_DB_PATH)

events = load_events(SYNTHETIC_DB_PATH)
patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
workflows = filter_meaningful_workflows(reconstruct_workflows(patterns))

print(f"Found {len(workflows)} meaningful workflow(s). Running full pipeline...\n")

for w in workflows:
    insight = analyze_workflow(w)
    score = compute_opportunity_score(w, insight)
    opportunity = Opportunity.from_pipeline_output(w, insight, score)
    save_opportunity(opportunity, APP_DB_PATH)
    print(f"Saved: {opportunity.workflow_name}  (score={opportunity.opportunity_score})")

print("\n--- Loading back from database ---")
stored = load_opportunities(APP_DB_PATH)
for o in stored:
    print(f"{o.opportunity_id[:8]}... | {o.workflow_name} | score={o.opportunity_score} | status={o.validation_status.value}")