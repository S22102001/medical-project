# hashing.py:

# goal:
# to provide functions to create hash - SHA-256

# why?
# to identify data errors 
# to create one stracture that collects all the data 

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

def canonical_json_bytes(data: Mapping[str, Any]) -> bytes:
    """
    Converts a Python mapping into a canonical JSON byte representation.
    """
    jaon_str= json.dumps(
        data,
        sort_keys=True, # Stable key ordering
        separators=(",", ":"), # No extra whitespace
        ensure_ascii=False, # Consistent Unicode handling
    )

    return jaon_str.encode("utf-8")

def sha256_hex_from_bytes(raw: bytes) -> str:
    # creates SHA-256 and returns str hex
    return hashlib.sha256(raw).hexdigest()

def sha256_hex_from_mapping(data: Mapping[str, Any])->str:
    # gets dict and returns sha256
    raw = canonical_json_bytes(data)
    return sha256_hex_from_bytes(raw)