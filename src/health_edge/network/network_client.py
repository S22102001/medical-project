# src/health_edge/network/network_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Union

from health_edge.domain.event import Event

@dataclass(frozen=True, slots=True)
class SendResult:
    # network send result
    # acked= True means the server acknoeledged receipt

    acked: bool
    status_code: int | None = None
    error: str | None = None

SendReturn= Union[bool, SendResult]

class NetworkClient(Protocol):
    # contract only
    # implementations (real or fake) must provide send_event
    def send_event(self, eveent: Event) -> SendReturn:
        ...