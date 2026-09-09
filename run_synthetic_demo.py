from friction_miner.synthetic.generator import generate_dataset
from friction_miner.storage.db import init_db, save_events, load_events, count_events

# 1. Generate synthetic events
events = generate_dataset(num_occurrences=20, noise_events=5)
print(f"Generated {len(events)} synthetic events\n")

# 2. Initialize DB and save
init_db()
save_events(events)
print(f"Saved to database. Total events in DB: {count_events()}\n")

# 3. Load back and verify
loaded = load_events()
print(f"Loaded {len(loaded)} events from database\n")

for e in loaded[:5]:
    print(f"{e.timestamp} | {e.application:10s} | {e.event_type.value}")