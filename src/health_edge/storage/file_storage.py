# file_storage.py

# goals:
# save events on local filesystem FIFO queue

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from health_edge.domain.event import Event
from health_edge.storage.storage_handler import StorageHandler, StorageStats
from health_edge.storage.crypto import (
    EncryptedBlob,
    load_key_from_env,
    encrypt_bytes,
    decrypt_bytes,
)

@dataclass(frozen=True)
class FileStorageConfig:
    base_dir: Path
    buffer_filename: str = "buffer.jsonl"
    cursor_filename: str = "cursor.txt"
    cursor_tmp_filename: str = "cursor.tmp"
    quarantine_filename: str = "quarantine.jsonl"
    encrypt_at_rest: bool = True  # LLD


class FileStorage(StorageHandler):
    """
    Append-only JSONL + cursor pointer (ACK moves cursor).
    Supports optional AES-256 encryption at rest + quarantine corrupted records.
    """

    def __init__(self, config: FileStorageConfig) -> None:
        self._cfg = config
        self._base = config.base_dir
        self._base.mkdir(parents=True, exist_ok=True)

        self._buffer_path = self._base / config.buffer_filename
        self._cursor_path = self._base / config.cursor_filename
        self._cursor_tmp_path = self._base / config.cursor_tmp_filename
        self._quarantine_path = self._base / config.quarantine_filename

        if not self._buffer_path.exists():
            self._buffer_path.write_text("", encoding="utf-8")
        if not self._cursor_path.exists():
            self._cursor_path.write_text("0", encoding="utf-8")
        if not self._quarantine_path.exists():
            self._quarantine_path.write_text("", encoding="utf-8")

        self._key = load_key_from_env() if config.encrypt_at_rest else None

    # ------------------------------
    # internal helpers
    # ------------------------------
    def _read_cursor(self) -> int:
        raw = self._cursor_path.read_text(encoding="utf-8").strip()
        return int(raw) if raw else 0

    def _write_cursor_atomic(self, value: int) -> None:
        self._cursor_tmp_path.write_text(str(value), encoding="utf-8")
        os.replace(self._cursor_tmp_path, self._cursor_path)

    def _line_count(self) -> int:
        text = self._buffer_path.read_text(encoding="utf-8")
        return 0 if not text.strip() else len(text.strip().splitlines())

    def _read_line_at(self, index: int) -> Optional[str]:
        lines = self._buffer_path.read_text(encoding="utf-8").splitlines()
        if index < 0 or index >= len(lines):
            return None
        return lines[index]

    def _serialize_event_line(self, event: Event) -> str:
        payload = json.dumps(event.to_dict(), ensure_ascii=False).encode("utf-8")
        if self._key is None:
            # plaintext (allowed only if encrypt_at_rest=False or key missing)
            return json.dumps({"v": 1, "plain": True, "data": event.to_dict()}, ensure_ascii=False)

        blob = encrypt_bytes(payload, self._key)
        return json.dumps(
            {"v": 1, "enc": True, "nonce": blob.nonce_b64, "ct": blob.ciphertext_b64},
            ensure_ascii=False,
        )

    def _deserialize_event_line(self, line: str) -> Event:
        obj = json.loads(line)

        # backward compatibility: old format might be direct event dict
        if isinstance(obj, dict) and "event_id" in obj:
            return Event.from_dict(obj)

        # plaintext wrapper
        if obj.get("plain") is True:
            return Event.from_dict(obj["data"])

        # encrypted wrapper
        if obj.get("enc") is True:
            if self._key is None:
                raise ValueError("Encrypted record found but no key configured in env")
            blob = EncryptedBlob(nonce_b64=obj["nonce"], ciphertext_b64=obj["ct"])
            raw = decrypt_bytes(blob, self._key)
            data = json.loads(raw.decode("utf-8"))
            return Event.from_dict(data)

        raise ValueError("Unknown record format")

    def _quarantine(self, index: int, raw_line: str, reason: str) -> None:
        q = {"index": index, "reason": reason, "raw": raw_line}
        with self._quarantine_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            f.flush()

    # ------------------------------
    # StorageHandler API
    # ------------------------------
    def append(self, event: Event) -> None:
        record = self._serialize_event_line(event)
        with self._buffer_path.open("a", encoding="utf-8") as f:
            f.write(record + "\n")
            f.flush()

    def read_next(self) -> Optional[Event]:
        cursor = self._read_cursor()
        raw_line = self._read_line_at(cursor)
        if raw_line is None:
            return None

        try:
            return self._deserialize_event_line(raw_line)
        except Exception as e:
            # LLD: corrupted record -> quarantine + continue
            self._quarantine(cursor, raw_line, f"{type(e).__name__}: {e}")
            # skip corrupted record safely
            self._write_cursor_atomic(cursor + 1)
            return self.read_next()

    def mark_acked(self, event_id: str) -> None:
        current = self.read_next()
        if current is None:
            return
        if current.event_id != event_id:
            raise ValueError("attempted to ACK wrong event")

        self._write_cursor_atomic(self._read_cursor() + 1)

    def has_pending(self) -> bool:
        return self._read_cursor() < self._line_count()

    def evict_low_priority(self, *, target_bytes: int) -> int:
        # best-effort MVP: not implemented yet (LLD item -> next step)
        if target_bytes <= 0:
             return 0

        before_size = self._buffer_path.stat().st_size
        cursor = self._read_cursor()
        lines = self._buffer_path.read_text(encoding="utf-8").splitlines()

        acked_lines = lines[:cursor]
        pending_lines = lines[cursor:]

        # Parse events + priority
        parsed: list[tuple[int, int, str]] = []  # (priority, idx_in_pending, raw_line)
        for idx, line in enumerate(pending_lines):
            try:
                ev = self._deserialize_event_line(line)
                pr = int(getattr(ev, "priority", 9999))
                parsed.append((pr, idx, line))
            except Exception as e:
                # corrupted: quarantine and treat as very low importance (removable)
                self._quarantine(cursor + idx, line, f"Corrupted during eviction: {type(e).__name__}: {e}")
                parsed.append((9999, idx, line))

        # candidates to evict: only priority > 1
        candidates = [(pr, idx, line) for (pr, idx, line) in parsed if pr > 1]

        # remove lowest importance first: highest priority number first
        # stable for same priority: smaller idx first
        candidates.sort(key=lambda t: (-t[0], t[1]))

        to_remove: set[int] = set()
        freed_est = 0

        for pr, idx, line in candidates:
            if freed_est >= target_bytes:
                break
            to_remove.add(idx)
            freed_est += len(line.encode("utf-8")) + 1

        # rewrite file preserving FIFO of retained lines
        new_pending = [line for i, line in enumerate(pending_lines) if i not in to_remove]
        new_lines = acked_lines + new_pending

        tmp_path = self._buffer_path.with_suffix(self._buffer_path.suffix + ".tmp")
        tmp_path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
        os.replace(tmp_path, self._buffer_path)

        after_size = self._buffer_path.stat().st_size
        return max(0, before_size - after_size)


    def get_stats(self) -> StorageStats:
        total = self._line_count()
        cursor = self._read_cursor()
        pending = max(0, total - cursor)
        approx_bytes = self._buffer_path.stat().st_size

        # NOTE: keep field names compatible with your tests (see storage_handler)
        return StorageStats(
            panding_count=pending,   # your current dataclass uses this typo
            approx_bytes=approx_bytes,
            disk_used_ratio=None,
        )

    def close(self) -> None:
        pass
