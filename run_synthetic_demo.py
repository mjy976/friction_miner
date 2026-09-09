from pathlib import Path

from friction_miner.synthetic.generator import generate_dataset
from friction_miner.storage.db import init_db, save_events, load_events, count_events

# Dedicated database for synthetic/test data — kept separate from
# data/friction_miner.db (real collector data), so we always have a
# clean dataset with a KNOWN ground truth (20 occurrences) to validate
# Pattern Mining against.
SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

events = generate_dataset(num_occurrences=20, noise_events=5)
print(f"Generated {len(events)} synthetic events\n")

init_db(SYNTHETIC_DB_PATH)
save_events(events, SYNTHETIC_DB_PATH)
print(f"Saved to database. Total events in DB: {count_events(SYNTHETIC_DB_PATH)}\n")

loaded = load_events(SYNTHETIC_DB_PATH)
print(f"Loaded {len(loaded)} events from database\n")

for e in loaded[:5]:
    print(f"{e.timestamp} | {e.application:10s} | {e.event_type.value}")