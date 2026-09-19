from pathlib import Path

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns
from friction_miner.workflow.reconstructor import reconstruct_workflows, filter_meaningful_workflows
from friction_miner.llm.analyzer import analyze_workflow

SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

events = load_events(SYNTHETIC_DB_PATH)
patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
workflows = filter_meaningful_workflows(reconstruct_workflows(patterns))

print(f"Found {len(workflows)} meaningful workflow(s). Sending to LLM...\n")

for w in workflows:
    print(f"--- Deterministic data ---")
    print(f"Steps: {' -> '.join(w.steps)}")
    print(f"Frequency: {w.frequency}, avg duration: {w.avg_duration_seconds:.1f}s\n")

    insight = analyze_workflow(w)

    print(f"--- LLM interpretation ---")
    print(f"Name: {insight.workflow_name}")
    print(f"Description: {insight.description}")
    print(f"Friction types: {[f.value for f in insight.friction_types]}")
    print(f"Automation potential: {insight.automation_potential:.0%}")
    print(f"Confidence: {insight.confidence:.0%}")
    print(f"Recommended solution: {insight.recommended_solution}")
    print(f"Automation level: {insight.estimated_automation_level.value}")
    print()