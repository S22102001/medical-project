# src/health_edge/network/network_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class NetworkClientError(Exception):
    """Base error for networking client."""


class NetworkUnavailableError(NetworkClientError):
    """Raised when the network is unavailable or request can't be completed."""


@dataclass
class NetworkResponse:
    ok: bool
    status_code: int = 200
    data: Optional[Any] = None
    error: Optional[str] = None


class NetworkClient:
    """
    Minimal NetworkClient implementation.
    This is enough for BufferManager imports/tests to run.

    You can later replace the internals with real HTTP logic.
    """

    def __init__(self, base_url: str | None = None, timeout_s: float = 5.0) -> None:
        self.base_url = base_url or ""
        self.timeout_s = timeout_s

    def is_available(self) -> bool:
        """
        For now: assume network is available.
        BufferManager usually just needs a boolean to decide whether to sync.
        """
        return True

    def send(self, payload: Any) -> NetworkResponse:
        """
        For now: pretend sending succeeded.
        Replace with real implementation (requests/httpx/urllib) later.
        """
        return NetworkResponse(ok=True, status_code=200, data={"sent": True})

    def close(self) -> None:
        """No-op for now (kept for API symmetry)."""
        return
