from pathlib import Path

from friction_miner.synthetic.generator import generate_persona_dataset, PERSONA_LABELS
from friction_miner.storage.db import init_db, save_events, count_events

SYNTHETIC_DB_PATH = Path("data/synthetic_events.db")

if SYNTHETIC_DB_PATH.exists():
    SYNTHETIC_DB_PATH.unlink()
    print(f"Removed old {SYNTHETIC_DB_PATH}\n")

events = generate_persona_dataset()

print(f"Generated {len(events)} synthetic events across {len(PERSONA_LABELS)} role-based workflows:")
for label in PERSONA_LABELS.values():
    print(f"  - {label}")
print()

init_db(SYNTHETIC_DB_PATH)
save_events(events, SYNTHETIC_DB_PATH)
print(f"Saved to database. Total events in DB: {count_events(SYNTHETIC_DB_PATH)}")