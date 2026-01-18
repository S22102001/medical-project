from health_edge.domain.event import Event, EventType

print("Creating event...")
e = Event.create(
    type=EventType.MEASUREMENT,
    priority=2,
    payload={"heart_rate": 88, "spo2": 97},
)

print("Event object:")
print(e)

print("\nEvent as dict:")
d = e.to_dict()
print(d)

print("\nRestoring event from dict...")
restored = Event.from_dict(d)

print("Restored event:")
print(restored)

print("\nHashes equal?")
print(e.hash == restored.hash)
