"""
Handler base class for the Sentinel Framework.

Defines the interface for event handlers that respond to KEL/TEL/Credential changes.
"""

from abc import ABC
import logging

from sentinel.framework.events import KELEvent, TELEvent, CredentialEvent

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Abstract base class for handling KEL/TEL/Credential events.

    Developers subclass this and implement only the methods they need.
    All methods are optional and default to no-op.
    Methods can be sync or async (async preferred for I/O operations).

    Example:
        class MyHandler(EventHandler):
            async def on_kel(self, event: KELEvent):
                print(f"KEL detected: {event.aid}")

        register_handler(MyHandler())
        run(export_dir="/usr/local/sentinel")
    """

    async def on_kel(self, event: KELEvent):
        """
        Called when a KEL file is new or modified.

        Args:
            event: KELEvent containing aid, data, filepath, timestamp, hby, essr, db

        Example:
            async def on_kel(self, event: KELEvent):
                aid = event.aid
                cesr_bytes = event.data
                filepath = event.filepath
                timestamp = event.timestamp
                # Your custom logic here
        """
        pass

    async def on_tel(self, event: TELEvent):
        """
        Called when a TEL file is new or modified.

        Args:
            event: TELEvent containing aid, data, filepath, timestamp, hby, essr, db

        Example:
            async def on_tel(self, event: TELEvent):
                print(f"TEL detected: {event.aid}")
        """
        pass

    async def on_credential(self, event: CredentialEvent):
        """
        Called when a credential file is new or modified.

        Args:
            event: CredentialEvent containing aid, data, filepath, timestamp, hby, essr, db

        Example:
            async def on_credential(self, event: CredentialEvent):
                print(f"Credential detected: {event.aid}")
        """
        pass
