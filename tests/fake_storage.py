from typing import List, Optional

from health_edge.domain.event import Event
from health_edge.storage.storage_handler import StorageHandler, StorageStats


class FakeStorage(StorageHandler):
    """In-memory StorageHandler for tests (no files, no persistence)."""

    def __init__(self) -> None:
        # Store appended events in arrival order (FIFO)
        self._events: List[Event] = []
        # Index of the next un-ACKed event
        self._cursor: int = 0

    def append(self, event: Event) -> None:
        # Append event to the in-memory list
        self._events.append(event)

    def read_next(self) -> Optional[Event]:
        # Return next pending event without removing it
        if self._cursor >= len(self._events):
            return None
        return self._events[self._cursor]

    def mark_acked(self, event_id: str) -> None:
        # Advance cursor only if the ACK matches the current event
        current = self.read_next()
        if current is None:
            return
        if current.event_id != event_id:
            raise ValueError("Attempted to ACK wrong event")
        self._cursor += 1

    def has_pending(self) -> bool:
        # True if there are un-ACKed events
        return self._cursor < len(self._events)

    def evict_low_priority(self, *, target_free_bytes: int) -> int:
        # Not needed for basic contract tests (no real storage pressure here)
        return 0

    def get_stats(self) -> StorageStats:
        pending = len(self._events) - self._cursor
        return StorageStats(pending_count=pending, approx_bytes=0, disk_used_ratio=None)

    def close(self) -> None:
        # Nothing to close for in-memory storage
        pass
