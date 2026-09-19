from pathlib import Path

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns
from friction_miner.workflow.reconstructor import reconstruct_workflows, filter_meaningful_workflows
from friction_miner.llm.analyzer import analyze_workflow
from friction_miner.scoring.opportunity_scorer import compute_opportunity_score

SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

events = load_events(SYNTHETIC_DB_PATH)
patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
workflows = filter_meaningful_workflows(reconstruct_workflows(patterns))

print(f"Found {len(workflows)} meaningful workflow(s)\n")

for w in workflows:
    insight = analyze_workflow(w)
    score = compute_opportunity_score(w, insight)

    print("=" * 60)
    print(f"Automation Opportunity: {insight.workflow_name}")
    print("=" * 60)
    print(f"Description         : {insight.description}")
    print()
    print(f"Frequency           : {score.frequency_per_week:.1f}/week")
    print(f"Time spent          : {score.time_spent_hours_per_week:.1f}h/week")
    print(f"Predictability      : {score.predictability:.0%}")
    print(f"Automation potential: {score.automation_potential:.0%}")
    print(f"Human judgment      : {score.human_judgment_required:.0%}")
    print()
    print(f"Opportunity Score   : {score.total_score}/100")
    print()
    print("Breakdown:")
    for name, values in score.breakdown.items():
        print(
            f"  {name:22s} raw={values['raw']:.2f}  "
            f"normalized={values['normalized']:.2f}  "
            f"weight={values['weight']:.2f}  "
            f"contribution={values['contribution']:.1f}"
        )
    print()
    print(f"Recommended solution: {insight.recommended_solution}")
    print()