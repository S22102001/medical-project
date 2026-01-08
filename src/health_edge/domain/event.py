# event.py

# goal:
# to define "Event" as a solid object 

# why?
# to prevent errors when passing loosely-typed dictionaries between layers

# the encoding will be added at-> storage/crypto.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional
from uuid import UUID, uuid4

from health_edge.utils.hashing import sha256_hex_from_mapping

class EventType(str, Enum): # Enum defines kinds of events that exists
    MEASUREMENT= "MEASUREMENT" # Regular physiological measurement
    ALERT= "ALERT" # Critical or abnormal event that requires immediate attention

@dataclass(frozen=True) # creates "const" object-> can't be changed
class Event:
    event_id: str # uniqe identifier of the event
    type: EventType # defines the type o the event-> MEASUREMENT, ALERT
    timestamp: str # time when the event occured -> Used for ordering, synchronization, and audit purposes
    priority: int # numerical priority level of the event 
    payload: Dict[str, Any] # the event data -> contains sensor values or alert details

    hash: str= field(default="") # calculated from hash

    def __post_init__(self) -> None: # runs right after creating the object __post_init__
        
        try: #first validation -> is UUID valid? 
            UUID(self.event_id)
        except Exception as e:
            raise ValueError(f"event_id must be a valid UUID string. Got: {self.event_id}") from e
        
        #validation 2 -> is priority is valid? (type and value)
        if not isinstance(self.priority,int):
            raise TypeError("priority must be int")
        
        if self.priority < 0 :
            raise ValueError("priority must be >=0")

        #validation 3 -> validation for timestamp 
        try:
            parsed= datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timestamp must include timezone (UTC)")
        except Exception as e:
            raise ValueError(f"timestamp must be ISO8601 UTC. Got: {self.timestamp}") from e
        
        #validation 4 -> payload
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")
        
        #validation 5 -> if hash calculation isn't provided
        if not self.hash:
            computed= self.compute_hash()
            object.__setattr__(self,"hash",computed)

    def to_dict(self) -> Dict[str, Any]: # convert events to dict
        return { # returns JSON
            "event_id": self.event_id, 
            "type": self.type, # convert Enum to string
            "timestamp": self.timestamp,
            "priority": self.priority,
            "payload": self.payload,
            "hash": self.hash,
        }
    
    def compute_hash(self)-> str: # calculates sha256 for hash
        data_without_hash: Mapping[str, Any] ={
            "event_id": self.event_id,
            "type": self.type,
            "timestamp": self.type,
            "priority": self.priority,
            "payload": self.payload,
        }
        return sha256_hex_from_mapping(data_without_hash)
    
    @staticmethod
    def now_utc_iso()-> str: #returns timestamp as ISO8601 format
        return datetime.now(timezone.utc).isoformat()
    
    @classmethod
    def create(
        cls,
        *,
        type: EventType,
        payload: Dict[str, Any],
        priority: int=1,
        event_id: Optional[str]= None,
        timestamp: Optional[str]= None,
    ) -> "Event": # an easy way to make an event without repeating on uuid or timestamp
        eid = event_id or str(uuid4())
        ts = timestamp or cls.now_utc_iso()
        return cls(
            event_id=eid,
            type=type,
            timestamp=ts,
            priority=priority,
            payload=payload,
        )
    
    @classmethod
    def from_dict(cls, data:Mapping[str, Any])-> "Event": # creates event from dict that comes from storage or network
        return cls(
            event_id=str(data["event_id"]),
            type=EventType(str(data["type"])),
            timestamp=str(data["timestapm"]),
            priority= int(data["priority"]),
            payload= dict(data.get("payload",{})),
            hash= str(data.get("hash", "")), 
        )
    