from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class InvalidTransition(Exception):
# רaised when a state transition is not allowed


class BufferState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    SYNC = "SYNC"


@dataclass
class StateMachine:
    state: BufferState = BufferState.ONLINE

    # Allowed transitions table (class-level constant)
    _ALLOWED_TRANSITIONS: ClassVar[dict[BufferState, set[BufferState]]] = {
        BufferState.ONLINE: {BufferState.OFFLINE},
        BufferState.OFFLINE: {BufferState.SYNC},
        BufferState.SYNC: {BufferState.ONLINE, BufferState.OFFLINE},
    }

    def can_transition_to(self, target: BufferState) -> bool:
        # True if target is allowed from current state
        return target in StateMachine._ALLOWED_TRANSITIONS.get(self.state, set())

    def transition_to(self, target: BufferState) -> None:
        # Perform transition if allowed; otherwise raise
        if not self.can_transition_to(target):
            raise InvalidTransition(f"Illegal transition: {self.state} -> {target}")
        self.state = target
