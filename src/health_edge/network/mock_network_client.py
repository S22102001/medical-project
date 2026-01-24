from __future__ import annotations

from dataclasses import dataclass, field

from health_edge.domain.event import Event


@dataclass
class MockNetworkClient:
    # simple controllable network client for demos/tests.
    # should_succeed=True: send_event returns True and records sent ids
    # should_succeed=False: send_event returns False

    should_succeed: bool = True
    sent_ids: list[str] = field(default_factory=list)

    def send_event(self, event: Event) -> bool:
        if self.should_succeed:
            self.sent_ids.append(event.event_id)
            return True
        return False
