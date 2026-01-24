# storage_handler.py

# goals:
# Define the interface forthe local persistent bufer storage.

# important concept:
# Describe WHAT operations storage MUST provide, NOT HOW they are implemented -> the actual implementation will be in "file_storage.py".

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from health_edge.domain.event import Event

@dataclass(frozen=True)

# small snapshot of the storage state
class StorageStats:
    panding_count: int # number of pending events
    approx_bytes: int # best effort estimate of how many bytes are stored for panding events
    disk_used_ratio: Optional[float] = None  # optional best effort of disk usage ratio

    @property
    def pending_count(self) -> int:
        return self.panding_count
    
# defines WHAT the local persistent buffer must support
class StorageHandler(ABC):

    @abstractmethod
    def append(self, event: Event) -> None:
    # persist a new event into local storage.
    # expectations:
    # 1. durable: after this returns, the event should survive a crash.
    # 2. append-only: preserves order of arrival.
        raise NotImplementedError()

    @abstractmethod
     # return the next pending event (FIFO) without removing it.
    def read_next(self) -> Optional[Event]:
        # returns:
        # 1. event: if there is at least one un-ACKed event.
        # 2. none: if no pending events exist.
       raise NotImplementedError()

    @abstractmethod
    # mark the current next event as acknowledged by the backend
    def mark_acked(self, event_id: str) -> None:
        # why event_id?
        # 1. safety check: ensures we ACK the exact event we just sent
        # 2. helps prevent cursor bugs (ACKing the wrong event)

        raise NotImplementedError()

    @abstractmethod
    # quick check if there are any pending events to sync?
    def has_pending(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    # best effort eviction under storage pressure
    def evict_low_priority(self, * , target_bytes: int) -> int:
    # target_free_bytes:
    #     how many bytes we aim to free
    # returns:
    #     how many bytes were actually freed (best effort)
        raise NotImplementedError()
    
    @abstractmethod
    # return best effort storage statistics
    def get_stats(self) -> StorageStats:
        raise NotImplementedError()

    @abstractmethod
    # realese resources- close files, flush buffers, etc.
    def close(self) -> None:
        raise NotImplementedError()
    
    

