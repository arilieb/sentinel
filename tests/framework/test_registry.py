"""
Tests for framework handler registry
"""

import pytest
from datetime import datetime
from sentinel.framework.handlers import EventHandler
from sentinel.framework.events import KELEvent, TELEvent, CredentialEvent
from sentinel.framework.registry import (
    HandlerRegistry,
    register_handler,
    unregister_handler,
    get_registry,
)


class CountingHandler(EventHandler):
    """Test handler that counts calls"""

    def __init__(self, name: str):
        self.name = name
        self.kel_count = 0
        self.tel_count = 0
        self.cred_count = 0

    async def on_kel(self, event: KELEvent):
        self.kel_count += 1

    async def on_tel(self, event: TELEvent):
        self.tel_count += 1

    async def on_credential(self, event: CredentialEvent):
        self.cred_count += 1


class FailingHandler(EventHandler):
    """Test handler that raises exceptions"""

    async def on_kel(self, event: KELEvent):
        raise ValueError("Intentional test error")


@pytest.fixture
def registry():
    """Get fresh registry for each test"""
    reg = HandlerRegistry()
    # Clear any existing handlers
    reg._handlers = set()
    return reg


class TestHandlerRegistry:
    """Test HandlerRegistry"""

    def test_registry_is_singleton(self):
        """Test that HandlerRegistry is a singleton"""
        reg1 = HandlerRegistry()
        reg2 = HandlerRegistry()
        assert reg1 is reg2

    def test_register_handler(self, registry):
        """Test registering a handler"""
        handler = CountingHandler("test")
        registry.register(handler)
        assert handler in registry.get_handlers()

    def test_register_invalid_handler(self, registry):
        """Test that registering non-handler raises TypeError"""
        with pytest.raises(TypeError):
            registry.register("not a handler")

    def test_unregister_handler(self, registry):
        """Test unregistering a handler"""
        handler = CountingHandler("test")
        registry.register(handler)
        assert handler in registry.get_handlers()

        registry.unregister(handler)
        assert handler not in registry.get_handlers()

    def test_get_handlers(self, registry):
        """Test getting all handlers"""
        handler1 = CountingHandler("test1")
        handler2 = CountingHandler("test2")

        registry.register(handler1)
        registry.register(handler2)

        handlers = registry.get_handlers()
        assert len(handlers) == 2
        assert handler1 in handlers
        assert handler2 in handlers

    @pytest.mark.asyncio
    async def test_dispatch_kel_event(self, registry):
        """Test dispatching KEL event to handlers"""
        handler1 = CountingHandler("test1")
        handler2 = CountingHandler("test2")

        registry.register(handler1)
        registry.register(handler2)

        event = KELEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )

        await registry.dispatch("kel", event)

        assert handler1.kel_count == 1
        assert handler2.kel_count == 1
        assert handler1.tel_count == 0
        assert handler2.tel_count == 0

    @pytest.mark.asyncio
    async def test_dispatch_tel_event(self, registry):
        """Test dispatching TEL event to handlers"""
        handler = CountingHandler("test")
        registry.register(handler)

        event = TELEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )

        await registry.dispatch("tel", event)

        assert handler.tel_count == 1
        assert handler.kel_count == 0

    @pytest.mark.asyncio
    async def test_dispatch_credential_event(self, registry):
        """Test dispatching credential event to handlers"""
        handler = CountingHandler("test")
        registry.register(handler)

        event = CredentialEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )

        await registry.dispatch("credential", event)

        assert handler.cred_count == 1
        assert handler.kel_count == 0

    @pytest.mark.asyncio
    async def test_error_isolation(self, registry):
        """Test that handler errors don't affect other handlers"""
        failing = FailingHandler()
        counting = CountingHandler("test")

        registry.register(failing)
        registry.register(counting)

        event = KELEvent(
            aid="test",
            filepath="/tmp/test.cesr",
            data=b"test",
            timestamp=datetime.now(),
        )

        # Should not raise despite failing handler
        await registry.dispatch("kel", event)

        # Counting handler should still have been called
        assert counting.kel_count == 1


class TestGlobalRegistry:
    """Test global registry functions"""

    def test_get_registry_returns_singleton(self):
        """Test that get_registry returns the singleton"""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_register_handler_global(self):
        """Test global register_handler function"""
        registry = get_registry()
        registry._handlers = set()  # Clear

        handler = CountingHandler("test")
        register_handler(handler)

        assert handler in registry.get_handlers()

    def test_unregister_handler_global(self):
        """Test global unregister_handler function"""
        registry = get_registry()
        registry._handlers = set()  # Clear

        handler = CountingHandler("test")
        register_handler(handler)
        assert handler in registry.get_handlers()

        unregister_handler(handler)
        assert handler not in registry.get_handlers()
