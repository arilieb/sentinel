"""
Tests for framework event handlers
"""

import pytest
from datetime import datetime
from sentinel.framework.handlers import EventHandler
from sentinel.framework.events import KELEvent, TELEvent, CredentialEvent


class TestEventHandler:
    """Test EventHandler base class"""

    def test_event_handler_is_abstract(self):
        """Test that EventHandler can be instantiated (ABC with optional methods)"""
        handler = EventHandler()
        assert isinstance(handler, EventHandler)

    @pytest.mark.asyncio
    async def test_default_on_kel_is_noop(self):
        """Test that default on_kel method is a no-op"""
        handler = EventHandler()
        event = KELEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )
        # Should not raise
        result = await handler.on_kel(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_default_on_tel_is_noop(self):
        """Test that default on_tel method is a no-op"""
        handler = EventHandler()
        event = TELEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )
        # Should not raise
        result = await handler.on_tel(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_default_on_credential_is_noop(self):
        """Test that default on_credential method is a no-op"""
        handler = EventHandler()
        event = CredentialEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )
        # Should not raise
        result = await handler.on_credential(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_handler_implementation(self):
        """Test that custom handlers can override methods"""

        class CustomHandler(EventHandler):
            def __init__(self):
                self.kel_called = False
                self.tel_called = False
                self.cred_called = False

            async def on_kel(self, event: KELEvent):
                self.kel_called = True

            async def on_tel(self, event: TELEvent):
                self.tel_called = True

            async def on_credential(self, event: CredentialEvent):
                self.cred_called = True

        handler = CustomHandler()

        await handler.on_kel(
            KELEvent(
                aid="test",
                filepath="/tmp/test.cesr",
                data=b"test",
                timestamp=datetime.now(),
            )
        )
        assert handler.kel_called

        await handler.on_tel(
            TELEvent(
                aid="test",
                filepath="/tmp/test.cesr",
                data=b"test",
                timestamp=datetime.now(),
            )
        )
        assert handler.tel_called

        await handler.on_credential(
            CredentialEvent(
                aid="test",
                filepath="/tmp/test.cesr",
                data=b"test",
                timestamp=datetime.now(),
            )
        )
        assert handler.cred_called
