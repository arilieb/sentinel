#!/usr/bin/env python3
"""
KERI Analyzer Example - Standalone Sentinel Framework Application with KERI Integration

This example demonstrates using the framework WITH KERI infrastructure.
It accesses the Habery instance to perform deep inspection of KEL events.

Usage:
    # Terminal 1: Start sentinel with export directory
    sentinel start -n mydb -a myalias --export-dir /tmp/sentinel-export

    # Terminal 2: Run this application (will create its own KERI database)
    python examples/keri_analyzer.py
"""

from sentinel.framework import EventHandler, register_handler, run, KELEvent


class KERIAnalyzer(EventHandler):
    """Analyze KEL events using KERI infrastructure"""

    async def on_kel(self, event: KELEvent):
        print(f"\n=== Analyzing KEL: {event.aid} ===")
        print(f"File: {event.filepath}")
        print(f"Size: {len(event.data)} bytes")
        print(f"Time: {event.timestamp}")

        # Access KERI infrastructure if provided
        if event.hby:
            print("\nKERI Analysis:")
            kever = event.hby.kevers.get(event.aid)
            if kever:
                print(f"  Sequence: {kever.sner.num}")
                print(f"  Witnesses: {len(kever.wits)}")
                print(f"  Witness list: {kever.wits}")
                print(f"  Keys: {kever.verfers}")
            else:
                print(f"  AID {event.aid} not found in local database")
                print(f"  (May need to sync from network)")
        else:
            print("\nKERI infrastructure not available")
            print("Run with name= parameter to enable KERI analysis")

        print("=" * 50 + "\n")


if __name__ == "__main__":
    print("Starting KERI Analyzer...")
    print("This will create a KERI database at /tmp/keri-analyzer")
    print("Watching /tmp/sentinel-export for KEL changes")
    print("Press Ctrl+C to stop\n")

    # Register the handler
    register_handler(KERIAnalyzer())

    # Run the framework WITH KERI infrastructure
    # This will initialize a Habery instance and pass it to handlers
    run(
        export_dir="/tmp/sentinel-export",
        poll_interval=2.0,
        name="analyzer_db",  # Framework will initialize Habery with this name
        base="/tmp/keri-analyzer",  # Database location
    )
