from pathlib import Path

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns
from friction_miner.workflow.reconstructor import reconstruct_workflows, filter_meaningful_workflows

REAL_DB_PATH = Path("data/friction_miner.db")

events = load_events(REAL_DB_PATH)
print(f"Loaded {len(events)} real events\n")

patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
print(f"Raw patterns found by miner: {len(patterns)}\n")

workflows = reconstruct_workflows(patterns)
print(f"Reconstructed into {len(workflows)} canonical workflow(s)\n")

workflows = filter_meaningful_workflows(workflows)
print(f"After filtering single-app noise: {len(workflows)} meaningful workflow(s)\n")

for w in workflows:
    steps_str = " -> ".join(w.steps)
    total_minutes = w.estimated_total_time_seconds / 60
    print(f"[{w.step_count}-step workflow]")
    print(f"  sequence         : {steps_str}")
    print(f"  frequency        : {w.frequency}")
    print(f"  absorbed patterns: {w.absorbed_subpatterns}")
    print(f"  avg duration     : {w.avg_duration_seconds:.1f}s per occurrence")
    print(f"  est. total time  : {total_minutes:.1f} minutes across all occurrences")
    print()