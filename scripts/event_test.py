from health_edge.domain.event import Event, EventType

e= Event.create(
    type= EventType.MEASUREMENT,
    priority=2,
    payload={"heart_rate": 88, "spo2": 97}
)

print("Event object:")
print(e)

print("\n Event as dict:")
print(e.to_dict())