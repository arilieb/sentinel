"""
Sentinel Framework for KEL/TEL/Credential Event Handling

Provides an event-driven API for building standalone applications that respond to
changes in exported KERI Key Event Logs (KEL), Transaction Event Logs (TEL),
and Credentials.

This framework enables developers to build separate applications (running as
independent processes) that watch sentinel's export directory and react to
file changes through a simple handler-based API.

Example usage:

    from sentinel.framework import EventHandler, register_handler, run, KELEvent

    class MyApp(EventHandler):
        async def on_kel(self, event: KELEvent):
            print(f"New KEL for {event.aid}")
            print(f"Data: {len(event.data)} bytes")

    register_handler(MyApp())
    run(export_dir="/usr/local/sentinel")

Key Features:
- Standalone applications - no integration with sentinel service required
- Simple handler-based API - implement only the methods you need
- Error isolation - handler failures don't affect other handlers
- Optional KERI integration - access hby/essr/db if provided
- Polling-based watching - no external dependencies

Public API:
- EventHandler: Base class for implementing handlers
- KELEvent, TELEvent, CredentialEvent: Event data classes
- register_handler: Register a handler instance
- unregister_handler: Unregister a handler instance
- run: Main entry point to start the framework
"""

from sentinel.framework.handlers import EventHandler
from sentinel.framework.events import KELEvent, TELEvent, CredentialEvent, BaseEvent
from sentinel.framework.registry import register_handler, unregister_handler
from sentinel.framework.runner import run

__all__ = [
    "EventHandler",
    "KELEvent",
    "TELEvent",
    "CredentialEvent",
    "BaseEvent",
    "register_handler",
    "unregister_handler",
    "run",
]
