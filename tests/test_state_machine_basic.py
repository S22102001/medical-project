import pytest

from health_edge.buffer.state_machine import BufferState, StateMachine, InvalidTransition

def test_initial_state_is_online():
#defualt state should be ONLINE
    sm = StateMachine()
    assert sm.state == BufferState.ONLINE

def test_online_to_offline_is_allowed():
# network failure should move system from ONLINE to OFFLINE
    sm = StateMachine()
    sm.transition_to(BufferState.OFFLINE)
    assert sm.state == BufferState.OFFLINE

def test_offline_to_sync_is_allowed():
# after offline period go to SYNC to flush pending events
    sm = StateMachine()
    sm.transition_to(BufferState.OFFLINE)
    sm.transition_to(BufferState.SYNC)
    assert sm.state == BufferState.SYNC

def test_sync_to_online_is_allowed():
# after succeessful sync, system returns to ONLINE
    sm = StateMachine()
    sm.transition_to(BufferState.OFFLINE)
    sm.transition_to(BufferState.SYNC)
    sm.transition_to(BufferState.ONLINE)
    assert sm.state == BufferState.ONLINE

def test_offline_to_online_is_not_allowed_directly():
# direct OFFLINE -> ONLINE is illegal, must go through SYNC
    sm = StateMachine()
    sm.transition_to(BufferState.OFFLINE)

    with pytest.raises(InvalidTransition):
        sm.transition_to(BufferState.ONLINE) 


