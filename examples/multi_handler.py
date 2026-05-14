#!/usr/bin/env python3
"""
Multi-Handler Example - Standalone Sentinel Framework Application

This example demonstrates using multiple handlers simultaneously.
Each handler operates independently with error isolation.

Usage:
    # Terminal 1: Start sentinel with export directory
    sentinel start -n mydb -a myalias --export-dir /tmp/sentinel-export

    # Terminal 2: Run this application
    python examples/multi_handler.py
"""

import json
from pathlib import Path
from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent, TELEvent, CredentialEvent


class FileLogger(EventHandler):
    """Log all events to a file"""

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def on_kel(self, event: KELEvent):
        with open(self.log_path, "a") as f:
            f.write(f"{event.timestamp} KEL {event.aid} {event.filepath}\n")

    async def on_tel(self, event: TELEvent):
        with open(self.log_path, "a") as f:
            f.write(f"{event.timestamp} TEL {event.aid} {event.filepath}\n")

    async def on_credential(self, event: CredentialEvent):
        with open(self.log_path, "a") as f:
            f.write(
                f"{event.timestamp} CREDENTIAL {event.aid} {event.filepath}\n"
            )


class MetricsCollector(EventHandler):
    """Collect metrics on events"""

    def __init__(self):
        self.kel_count = 0
        self.tel_count = 0
        self.cred_count = 0

    async def on_kel(self, event: KELEvent):
        self.kel_count += 1
        print(f"[Metrics] Total KELs: {self.kel_count}")

    async def on_tel(self, event: TELEvent):
        self.tel_count += 1
        print(f"[Metrics] Total TELs: {self.tel_count}")

    async def on_credential(self, event: CredentialEvent):
        self.cred_count += 1
        print(f"[Metrics] Total Credentials: {self.cred_count}")


class AlertSystem(EventHandler):
    """Alert on specific identifiers"""

    def __init__(self, watched_aids: list):
        self.watched_aids = set(watched_aids)

    async def on_kel(self, event: KELEvent):
        if event.aid in self.watched_aids:
            print(f"\n*** ALERT: Watched identifier {event.aid} changed! ***\n")

    async def on_tel(self, event: TELEvent):
        if event.aid in self.watched_aids:
            print(f"\n*** ALERT: Watched TEL {event.aid} changed! ***\n")


class DataExporter(EventHandler):
    """Export event data to JSON"""

    def __init__(self, export_dir: str):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def on_kel(self, event: KELEvent):
        metadata = {
            "type": "KEL",
            "aid": event.aid,
            "filepath": event.filepath,
            "timestamp": event.timestamp.isoformat(),
            "size": len(event.data),
        }
        output_path = self.export_dir / f"kel_{event.aid}_{event.timestamp.timestamp()}.json"
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"[Exporter] Exported KEL metadata to {output_path}")


if __name__ == "__main__":
    print("Starting Multi-Handler Example...")
    print("Registered handlers:")
    print("  1. FileLogger - logs to /tmp/sentinel-events.log")
    print("  2. MetricsCollector - counts events")
    print("  3. AlertSystem - alerts on specific AIDs")
    print("  4. DataExporter - exports metadata to JSON")
    print("\nPress Ctrl+C to stop\n")

    # Register all handlers
    register_handler(FileLogger(log_path="/tmp/sentinel-events.log"))
    register_handler(MetricsCollector())
    register_handler(
        AlertSystem(
            watched_aids=[
                # Add AIDs to watch here
                # "EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM",
            ]
        )
    )
    register_handler(DataExporter(export_dir="/tmp/sentinel-exports"))

    # Run the framework
    run(
        export_dir="/tmp/sentinel-export",
        poll_interval=2.0,
    )
