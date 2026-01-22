import pytest

from health_edge.domain.event import Event, EventType
from health_edge.storage.file_storage import FileStorage, FileStorageConfig

def create_sample_event(i: int) -> Event:
    # helper to generate a deterministic sample event
    return Event.create(
        type= EventType.MEASUREMENT,
        priority=1,
        payload={"value": i},
    )

def test_file_storage_append_the_read_next(tmp_path):
    # test basic storgae on disk
    # add events to file (append)
    # read the next in line (read_next)
    # make sure it's the same event

    storage= FileStorage(FileStorageConfig(base_dir=tmp_path))

    e= create_sample_event(1)
    storage.append(e)

    fetched= storage.read_next()
    assert fetched is not None
    assert fetched.event_id == e.event_id

def test_file_storage_fifo_and_ack(tmp_path):
    # check FIFO behavior + ACK handling
    # append two events
    # read the first and ACK it
    # read next should return the second event

    storage= FileStorage( FileStorageConfig(base_dir= tmp_path))

    e1= create_sample_event(1)
    e2= create_sample_event(2)

    storage.append(e1)
    storage.append(e2)

    first= storage.read_next()
    assert first is not None
    assert first.event_id == e1.event_id

    storage.mark_acked(first.event_id)

    second= storage.read_next()
    assert second is not None
    assert second.event_id == e2.event_id

def test_file_storage_persists_cursor_after_restart(tmp_path):
    # test that represting the recovery of the storage handler
    # write to file and advance cursor
    # re-create FileStorage
    # test cursor is preserved and read_next should return the next correct event
    cfg= FileStorageConfig(base_dir= tmp_path)

    storage1= FileStorage(cfg)
    e1= create_sample_event(1)
    e2= create_sample_event(2)

    storage1.append(e1)
    storage1.append(e2)

    # ACK first event
    first= storage1.read_next()
    assert first is not None
    storage1.mark_acked(first.event_id)

    # restart- create a new instance reading the same files
    storage2= FileStorage(cfg)
    next_after_restart= storage2.read_next()

    assert next_after_restart is not None
    assert next_after_restart.event_id == e2.event_id