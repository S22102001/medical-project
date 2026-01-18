from health_edge.domain.event import Event, EventType


# verify that reating an Event automatically generates hash, uuid, and timestamp
def test_event_create_generates_hash_uuid_timestamp():
    e= Event.create(
        type= EventType.MEASUREMENT,
        priority=2,
        payload= {"heart_rate":88, "spo2":97},
    )
    
    # hash should be a SHA256 hex string (64 chars)
    assert isinstance(e.hash, str)
    assert len(e.hash) ==64

    #event_id should exist (!= NULL)
    assert isinstance(e.event_id, str)
    assert len(e.event_id) >0

    # timestamp should exist (!= NULL)
    assert isinstance(e.timestamp, str)
    assert len(e.timestamp) >0

# verify that Event.to_dict() converts the the EventType enum into a plain string => making it JSON friendly
def test_event_to_dict_type_is_string():
    e= Event.create(
        type= EventType.MEASUREMENT,
        payload= {"x":1},
    )
    d= e.to_dict()
    
    ## 'type' must be a string, not an enum object
    assert d["type"] == "MEASUREMENT"

# verify that converting an Event to dict and back to Event preserves the original data and core fields
def test_event_roundtrip_preserves_hash():
    e= Event.create(
        type= EventType.ALERT,
        priority=5,
        payload= {"alert": True , "score": 0.91},
    )
    d= e.to_dict()
    restored= Event.from_dict(d)

    # all core fields must be identical
    assert restored.event_id == e.event_id
    assert restored.hash == e.hash
    assert restored.type == EventType.ALERT
    assert restored.to_dict()["type"] == "ALERT"