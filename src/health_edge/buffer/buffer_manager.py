from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from health_edge.domain.event import Event
from health_edge.storage.storage_handler import StorageHandler
from health_edge.buffer.state_machine import StateMachine, BufferState
from health_edge.network.network_client import NetworkClient, SendResult

class SyncAlradyRunning(RuntimeError):
    # raised when sync is requested whilee a sync is already in progress
    pass

@dataclass
class BufferManager:
    storage: StorageHandler # persistent FIFO queue (FileStorage) holding not-yet-acked events
    client: NetworkClient # network dependency used to send events (mockable)
    state_machine: StateMachine = field(default_factory=StateMachine) # current connectivity/sync state (ONLINE/OFFLINE/SYNC)
    _sync_in_progress: bool=False # guard to ensure only one sync runs at a time 

    def ingest(self,event: Event) -> bool:
        # returns:
        # True-> event was sent successfully 
        # False-> evnt was buffered for later sync

        # ONLINE -> try send immediatly
        if self.state_machine.state == BufferState.ONLINE:
            # attempt network send first
            if self._is_acked(self.client.send_event(event)):
                return True
        
            # network failed -> OFFINE
            self.state_machine.transition_to(BufferState.OFFLINE)
            self.storage.append(event)
            return False
        
        # OFFLINE or SYNC -> always persist locally 
        self.storage.append(event)
        return False
    
    def start_sync(self)->None:
        # only if we're OFFLINE and there's no other running sync
        if self._sync_in_progress:
            raise SyncAlradyRunning("sync is alrady running")
        
        # we only allow sync from OFFLINE 
        if self.state_machine.state != BufferState.OFFLINE:
            # if ONLINE -> no need to sync
            # if already sync -> running
            if self.state_machine.state == BufferState.ONLINE:
                return
            raise SyncAlradyRunning("cannot start sync unless state is OFFLINE")
        
        self.state_machine.transition_to(BufferState.SYNC)
        self._sync_in_progress= True
    
    def sync_step(self, *, max_batch: int=50) -> int:
        # run a single sync batch
        # returns: number of events successfully synced 
        if not self._sync_in_progress:
            return 0
        
        acked= 0

        for _ in range(max_batch):
            next_event: Optional[Event]= self.storage.read_next()
            if next_event is None:
                # nothing pending -> finish sync successfully
                self._finish_sync_success()
                break

            # try send
            if self._is_acked(self.client.send_event(next_event)):
                self.storage.mark_acked(next_event.event_id)
                acked += 1
                continue

            # send failed -> go back to OFFLLINE 
            self._finish_sync_failed()
            break

        return acked
    
    def _finish_sync_success(self) -> None:
        # sync completed, return to ONLINE
        self._sync_in_progress= False
        self.state_machine.transition_to(BufferState.ONLINE)

    def _finish_sync_failed(self)-> None:
        # sync interrupted by network failure, go back to OFFLINE
        self._sync_in_progress= False
        self.state_machine.transition_to(BufferState.OFFLINE)

    def _is_acked(self, result) -> bool:
        # supports both bool and SendResult
        if isinstance(result,bool):
            return result
        
        # support SendResult / objects that expose ".acked"
        return bool(getattr(result,"acked", False)) 