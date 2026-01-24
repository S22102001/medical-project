import argparse
import os
from pathlib import Path

from health_edge.domain.event import Event, EventType
from health_edge.buffer.buffer_manager import BufferManager
from health_edge.buffer.state_machine import BufferState
from health_edge.storage.file_storage import FileStorage, FileStorageConfig
from health_edge.network.mock_network_client import MockNetworkClient


BASE_DIR = Path("demo_storage")


def create_manager(network_ok: bool) -> BufferManager:
    storage = FileStorage(FileStorageConfig(base_dir=BASE_DIR))
    client = MockNetworkClient(should_succeed=network_ok)
    return BufferManager(storage=storage, client=client)


def cmd_ingest(args):
    bm = create_manager(network_ok=not args.offline)
    event = Event.create(
        type=EventType.MEASUREMENT,
        priority=args.priority,
        payload={"value": args.value},
    )
    sent = bm.ingest(event)
    print(f"Ingested event {event.event_id}, sent={sent}")


def cmd_offline(args):
    print("Simulating OFFLINE mode")
    bm = create_manager(network_ok=False)
    bm.state_machine.transition_to(BufferState.OFFLINE)
    print("State:", bm.state_machine.state)


def cmd_online(args):
    print("Simulating ONLINE mode")
    bm = create_manager(network_ok=True)
    bm.state_machine.transition_to(BufferState.ONLINE)
    print("State:", bm.state_machine.state)


def cmd_sync(args):
    bm = create_manager(network_ok=True)

    # if we have pending events, we must be in OFFLINE to start sync
    if bm.storage.has_pending() and bm.state_machine.state != BufferState.OFFLINE:
        bm.state_machine.transition_to(BufferState.OFFLINE)

    bm.start_sync()
    acked = bm.sync_step(max_batch=50)
    print(f"Synced {acked} events")

def cmd_status(args):
    storage = FileStorage(FileStorageConfig(base_dir=BASE_DIR))
    stats = storage.get_stats()
    print("Pending events:", stats.panding_count)
    print("Approx bytes:", stats.approx_bytes)


def main():
    parser = argparse.ArgumentParser(description="Medical Edge Buffer Demo CLI")
    sub = parser.add_subparsers()

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--value", type=int, required=True)
    p_ingest.add_argument("--priority", type=int, default=1)
    p_ingest.add_argument("--offline", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

    p_offline = sub.add_parser("offline")
    p_offline.set_defaults(func=cmd_offline)

    p_online = sub.add_parser("online")
    p_online.set_defaults(func=cmd_online)

    p_sync = sub.add_parser("sync")
    p_sync.set_defaults(func=cmd_sync)

    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
