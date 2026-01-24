import base64
import os
from pathlib import Path

import pytest

from health_edge.domain.event import Event, EventType
from health_edge.storage.file_storage import FileStorage, FileStorageConfig

ENV_KEY_NAME= "HEALTH_EDGE_AES_KEY_B64"

def set_key(monkeypatch):
    key= os.urandom(32)
    monkeypatch.setenv(ENV_KEY_NAME, base64.b64encode(key).decode("ascii"))

def create_event(v: int, priority: int=1)-> Event:
    return Event.create(
        type=EventType.MEASUREMENT,
        priority=priority,
        payload={"value": v},
    )

def test_quarantine_corrupted_record(monkeypatch, tmp_path: Path):
    # key optional here - we just need storage to work
    storage = FileStorage(FileStorageConfig(base_dir=tmp_path))

    e1 = create_event(1)
    e2 = create_event(2)
    storage.append(e1)

    # inject corrupted line between events
    buf = tmp_path / "buffer.jsonl"
    with buf.open("a", encoding="utf-8") as f:
        f.write("NOT_JSON\n")

    storage.append(e2)

    first = storage.read_next()
    assert first is not None and first.event_id == e1.event_id
    storage.mark_acked(e1.event_id)

    # should skip corrupted and return e2
    second = storage.read_next()
    assert second is not None and second.event_id == e2.event_id

    q = (tmp_path / "quarantine.jsonl").read_text(encoding="utf-8")
    assert "NOT_JSON" in q

def test_evict_low_priority_frees_space(monkeypatch, tmp_path: Path):
    # key optional here too
    storage = FileStorage(FileStorageConfig(base_dir=tmp_path))

    high = create_event(10, priority=1)   # keep
    low1 = create_event(11, priority=5)   # remove first
    low2 = create_event(12, priority=5)   # remove next

    storage.append(high)
    storage.append(low1)
    storage.append(low2)

    before = (tmp_path / "buffer.jsonl").stat().st_size
    freed = storage.evict_low_priority(target_bytes=1)
    after = (tmp_path / "buffer.jsonl").stat().st_size

    assert freed > 0
    assert after < before

    # ensure FIFO of retained events starts with high
    nxt = storage.read_next()
    assert nxt is not None and nxt.event_id == high.event_id

def test_encrypt_at_rest_no_plaintext_when_key_set(monkeypatch, tmp_path: Path):
    # only run this if you actually want encryption as a required LLD feature
    set_key(monkeypatch)

    storage = FileStorage(FileStorageConfig(base_dir=tmp_path, encrypt_at_rest=True))
    e = create_event(123)
    storage.append(e)

    raw = (tmp_path / "buffer.jsonl").read_text(encoding="utf-8")

    # payload value should not appear in cleartext when encrypted
    assert "123" not in raw
    assert "payload" not in raw