#!/usr/bin/env python3
"""
Simple Logger Example - Standalone Sentinel Framework Application

This example demonstrates the basic usage of the Sentinel Framework.
It logs all KEL/TEL/Credential events to stdout without requiring KERI dependencies.

Usage:
    # Terminal 1: Start sentinel with export directory
    sentinel start -n mydb -a myalias --export-dir /tmp/sentinel-export

    # Terminal 2: Run this application
    python examples/simple_logger.py
"""

from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent, TELEvent, CredentialEvent


class SimpleLogger(EventHandler):
    """Simple logger that prints all events to stdout"""

    async def on_kel(self, event: KELEvent):
        print(f"\n=== KEL Event ===")
        print(f"AID: {event.aid}")
        print(f"File: {event.filepath}")
        print(f"Size: {len(event.data)} bytes")
        print(f"Time: {event.timestamp}")
        print(f"=================\n")

    async def on_tel(self, event: TELEvent):
        print(f"\n=== TEL Event ===")
        print(f"AID: {event.aid}")
        print(f"File: {event.filepath}")
        print(f"Size: {len(event.data)} bytes")
        print(f"Time: {event.timestamp}")
        print(f"=================\n")

    async def on_credential(self, event: CredentialEvent):
        print(f"\n=== Credential Event ===")
        print(f"AID: {event.aid}")
        print(f"File: {event.filepath}")
        print(f"Size: {len(event.data)} bytes")
        print(f"Time: {event.timestamp}")
        print(f"========================\n")


if __name__ == "__main__":
    print("Starting Simple Logger...")
    print("Watching /tmp/sentinel-export for KEL/TEL/Credential changes")
    print("Press Ctrl+C to stop\n")

    # Register the handler
    register_handler(SimpleLogger())

    # Run the framework (blocks until SIGINT/SIGTERM)
    run(
        export_dir="/tmp/sentinel-export",
        poll_interval=2.0,
    )
