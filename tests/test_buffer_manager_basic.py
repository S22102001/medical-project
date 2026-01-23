import pytest

from health_edge.buffer.buffer_manager import BufferManager, SyncAlradyRunning
from health_edge.buffer.state_machine import BufferState
from health_edge.domain.event import Event, EventType
from tests.fake_storage import FakeStorage

class FakeNeworkClient:
    # simple controllable fake network client for tests.
    # when should_succeed=True: send_event returns True
    # when should_succeed=False: send_event returns False
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.sent_ids: list[str] = []
    
    def send_event(self, event: Event)-> bool:
        if self.should_succeed:
            self.sent_ids.append(event.event_id)
            return True
        return False
    
def create_event(v: int) -> Event:
    return Event.create(
        type=EventType.MEASUREMENT,
        priority= 1,
        payload= {"value": v},
    )

def test_ingest_online_success_sends_without_buffering():
    storage= FakeStorage()
    net= FakeNeworkClient(should_succeed=True)
    bm= BufferManager(storage= storage, client= net)

    e= create_event(1)
    sent= bm.ingest(e)

    assert sent is True
    assert storage.has_pending() is False
    assert e.event_id in net.sent_ids
    assert bm.state_machine.state == BufferState.ONLINE

def test_ingest_online_failure_buffers_and_goes_offline():
    storage= FakeStorage()
    net= FakeNeworkClient(should_succeed=False)
    bm= BufferManager(storage= storage, client= net)

    e= create_event(1)
    sent= bm.ingest(e)

    assert sent is False
    assert storage.has_pending() is True
    assert bm.state_machine.state == BufferState.OFFLINE

def test_sync_flushes_fifo_and_returns_online():
    storage= FakeStorage()
    net= FakeNeworkClient(should_succeed=False)
    bm= BufferManager(storage= storage, client= net)

    # first ingest fails -> offline + buffered
    e1= create_event(1)
    e2= create_event(2)
    bm.ingest(e1)
    bm.ingest(e2)

    assert bm.state_machine.state == BufferState.OFFLINE
    assert storage.has_pending() is True

    # network comes back
    net.should_succeed= True

    bm.start_sync()
    acked= bm.sync_step(max_batch=10)

    assert acked ==2
    assert storage.has_pending() is False
    assert bm.state_machine.state == BufferState.ONLINE
    assert e1.event_id in net.sent_ids
    assert e2.event_id in net.sent_ids

def test_sync_failure_stops_and_rturns_offline():
    storage= FakeStorage()
    net= FakeNeworkClient(should_succeed=True)
    bm = BufferManager(storage=storage, client=net)

    # force offline mode with buffered events
    bm.state_machine.transition_to(BufferState.OFFLINE)
    e1 = create_event(1)
    e2 = create_event(2)
    storage.append(e1)
    storage.append(e2)

    bm.start_sync()

    # first send succeeds, then fail mid-sync
    net.should_succeed = True
    acked_first = bm.sync_step(max_batch=1)
    assert acked_first == 1
    assert storage.has_pending() is True
    assert bm.state_machine.state == BufferState.SYNC

    net.should_succeed = False
    acked_second = bm.sync_step(max_batch=10)

    assert acked_second == 0
    assert storage.has_pending() is True  # still one pending
    assert bm.state_machine.state == BufferState.OFFLINE

def test_no_parallel_sync():
    storage= FakeStorage()
    net= FakeNeworkClient(should_succeed=True)
    bm = BufferManager(storage=storage, client=net)

    bm.state_machine.transition_to(BufferState.OFFLINE)
    bm.start_sync()

    with pytest.raises(SyncAlradyRunning):
        bm.start_sync()
    

