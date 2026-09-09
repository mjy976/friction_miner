from pathlib import Path

from friction_miner.storage.db import load_events
from friction_miner.mining.sequence_miner import mine_patterns

SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

events = load_events(SYNTHETIC_DB_PATH)
print(f"Loaded {len(events)} events for pattern mining\n")

patterns = mine_patterns(events, min_n=2, max_n=6, min_frequency=3)
print(f"Found {len(patterns)} recurring patterns (frequency >= 3)\n")

for p in patterns[:15]:
    seq_str = " -> ".join(p.sequence)
    print(f"[{p.length}-step] freq={p.frequency:3d} | avg_duration={p.avg_duration_seconds:6.1f}s | {seq_str}")