from friction_miner.synthetic.generator import generate_dataset

events = generate_dataset(num_occurrences=20, noise_events=5)

print(f"Total events generated: {len(events)}\n")

for e in events[:10]:
    print(f"{e.timestamp} | {e.application:10s} | {e.event_type.value}")

print("\n... (showing first 10 of {} events)".format(len(events)))