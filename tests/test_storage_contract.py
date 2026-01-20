import pytest
from tests.fake_storage import FakeStorage

from health_edge.domain.event import Event, EventType
from health_edge.storage.storage_handler import StorageHandler

def create_sample_event(i: int) -> Event:

    return Event.create(
        type=EventType.MEASUREMENT,
        priority=1,
        payload={"value": i},
    )

#append followed by read_next() should return the same event
def test_append_then_read_next_returns_event(storage: StorageHandler):
    event = create_sample_event(1)

    storage.append(event)
    fetched = storage.read_next()

    assert fetched is not None
    assert fetched.event_id == event.event_id

#storage should return events in order -> FIFO
def test_fifo_order_is_preserved(storage: StorageHandler):
    event1 = create_sample_event(1)
    event2 = create_sample_event(2)

    storage.append(event1)
    storage.append(event2)


    first= storage.read_next()
    assert first.event_id == event1.event_id

    storage.mark_acked(first.event_id)

    second= storage.read_next()
    assert second.event_id == event2.event_id

#mark_acked should advance the internal cursor
def test_mark_acked_advances_to_next_event(storage: StorageHandler):
    event1= create_sample_event(1)
    event2= create_sample_event(2)

    storage.append(event1)
    storage.append(event2)

    storage.mark_acked(event1.event_id)

    next_event = storage.read_next()     
    assert next_event is not None
    assert next_event.event_id == event2.event_id

#has panding() should reflect whether pending event exists
def test_has_pending_reflects_storage_state(storage: StorageHandler):
    assert storage.has_pending() is False

    event = create_sample_event(1)
    storage.append(event)
    
    assert storage.has_pending() is True

    storage.mark_acked(event.event_id)
    assert storage.has_pending() is False

# provides a FakeStorage instance for testing
@pytest.fixture
def storage():
    return FakeStorage()

