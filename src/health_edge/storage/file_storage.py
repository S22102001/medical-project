# file_storage.py

# goals:
# save events on local filesystem FIFO queue

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from health_edge.domain.event import Event
from health_edge.storage.storage_handler import StorageHandler, StorageStats

@dataclass
# holds file locations used by FileStorage
class FileStorageConfig:
    base_dir: Path #directory on disk where run time storage files live
    buffer_filename: str = "buffer.jsonl" #append only json lines file (one event per line)
    cursor_filename: str = "cursor.txt" # text file storing the next panding event index
    cursor_tmp_filename: str = "cursor.tmp" # temporary cursor file for atomic updates

class FileStorage(StorageHandler):
# append only logs + cursor pointer for ACK based progress
# events are stored in a json lines file
# curser points to the next event to be processed
# mark_acked advances the cursor
    def __init__(self, config: FileStorageConfig)-> None:
        self._cfg= config
        self._base = config.base_dir
        self._base.mkdir(parents=True, exist_ok=True)

        self._buffer_path = self._base / config.buffer_filename
        self._cursor_path = self._base / config.cursor_filename
        self._cursor_tmp_path = self._base / config.cursor_tmp_filename

        # ensure files exist
        if not self._buffer_path.exists():
            self._buffer_path.write_text("", encoding="utf-8")
        if not self._cursor_path.exists():
            self._cursor_path.write_text("0", encoding="utf-8")
    
    #------------------------------
    # internal helpers
    #------------------------------
    
    def _read_cursor(self) -> int:
        # read cursor index from cursor.txt -> cursor is the next pending index
        raw= self._cursor_path.read_text(encoding="utf-8").strip()
        if raw == "":
            return 0
        return int(raw)

    def _write_cursor_atomic(self, value: int) -> None:
        #   atomic cursor update: write tmp then replace.
        self._cursor_tmp_path.write_text(str(value), encoding="utf-8")
        os.replace(self._cursor_tmp_path, self._cursor_path)
    
    def _line_count(self)->int: 
        # return number of events in the buffer file -> total appended records
        text= self._buffer_path.read_text(encoding="utf-8")
        if not text.strip():
            return 0
        return len(text.strip().splitlines())
    
    def _read_line_at(self, index: int) -> Optional[Event]:
        # simple implementation for MVP: reads all lines
        lines = self._buffer_path.read_text(encoding="utf-8").splitlines()
        if index < 0 or index >= len(lines):
            return None
        return lines[index]

    #------------------------------
    # StorageHandler API
    #------------------------------
    
    def append(self, event: Event) -> None:
        # append a single json record (flush to reduce loss on crash)
        record = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._buffer_path.open("a", encoding="utf-8") as f:
            f.write(record + "\n")
            f.flush()

    def read_next(self)-> Optional [Event]:
        # peek next pending event by cursor index
        cursor = self._read_cursor()
        raw_line= self._read_line_at(cursor)
        if raw_line is None:
            return None
        data= json.loads(raw_line)
        return Event.from_dict(data)
    
    def mark_acked(self, event_id:str)-> None:
        # advance cursor when ACK matches current pending event
        current= self.read_next()
        if current is None:
            return
        
        if current.event_id != event_id:
            raise ValueError("attempted to ACK wrong event")
        
        new_cursor= self._read_cursor() + 1
        self._write_cursor_atomic(new_cursor)
    
    def has_pending(self)-> bool:
        # pending exists if cursor < totla records
        return self._read_cursor() < self._line_count()
    
    def evict_low_priority(self, *, target_free_bytes: int)-> int:
        # no implemented in MVP, returns 0
        return 0
    
    def get_stats(self) -> StorageStats:
    # return current storage statistics for monitoring and control logic
        total_events= self._line_count()
        cursor= self._read_cursor()
        pending= max(0, total_events - cursor)

        approx_bytes= self._buffer_path.stat().st_size

        return StorageStats(
            pending_count= pending,
            approx_bytes= approx_bytes,
            disk_used_ratio=None,
        )
    
    def close(self) -> None:
        # no persistent open handles in MVP
        pass

