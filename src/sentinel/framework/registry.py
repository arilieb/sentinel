"""
Handler registry for the Sentinel Framework.

Provides singleton registry for managing event handlers and dispatching events.
"""

import logging
import asyncio
import inspect
from typing import List, Set

from sentinel.framework.handlers import EventHandler
from sentinel.framework.events import BaseEvent

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """
    Singleton registry for managing event handlers.

    Provides registration, deregistration, and event dispatching with error isolation.
    Each handler is called independently - if one fails, others still execute.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Set[EventHandler] = set()
        return cls._instance

    def register(self, handler: EventHandler):
        """
        Register an event handler.

        Args:
            handler: EventHandler instance to register

        Raises:
            TypeError: If handler is not an EventHandler instance
        """
        if not isinstance(handler, EventHandler):
            raise TypeError(
                f"Handler must be an EventHandler instance, got {type(handler)}"
            )
        self._handlers.add(handler)
        logger.info(f"Registered handler: {handler.__class__.__name__}")

    def unregister(self, handler: EventHandler):
        """
        Unregister an event handler.

        Args:
            handler: EventHandler instance to unregister
        """
        self._handlers.discard(handler)
        logger.info(f"Unregistered handler: {handler.__class__.__name__}")

    def get_handlers(self) -> List[EventHandler]:
        """
        Get all registered handlers.

        Returns:
            List of registered EventHandler instances
        """
        return list(self._handlers)

    async def dispatch(self, event_type: str, event: BaseEvent):
        """
        Dispatch an event to all registered handlers.

        Each handler is called independently with error isolation.
        If one handler fails, others still execute.

        Args:
            event_type: Event type ('kel', 'tel', 'credential')
            event: Event data (KELEvent, TELEvent, or CredentialEvent)

        Example:
            await registry.dispatch('kel', KELEvent(...))
        """
        method_name = f"on_{event_type}"

        for handler in self._handlers:
            try:
                method = getattr(handler, method_name, None)
                if method is None:
                    continue

                # Call method (supports both sync and async)
                if inspect.iscoroutinefunction(method):
                    await method(event)
                else:
                    method(event)

            except Exception as e:
                logger.exception(
                    f"Error in handler {handler.__class__.__name__}.{method_name}: {e}"
                )
                # Continue to next handler despite error


# Global registry instance
_registry = HandlerRegistry()


def register_handler(handler: EventHandler):
    """
    Register a handler with the global registry.

    Args:
        handler: EventHandler instance to register

    Example:
        class MyHandler(EventHandler):
            async def on_kel(self, event: KELEvent):
                print(f"KEL: {event.aid}")

        register_handler(MyHandler())
    """
    _registry.register(handler)


def unregister_handler(handler: EventHandler):
    """
    Unregister a handler from the global registry.

    Args:
        handler: EventHandler instance to unregister
    """
    _registry.unregister(handler)


def get_registry() -> HandlerRegistry:
    """
    Get the global registry instance.

    Returns:
        The singleton HandlerRegistry instance
    """
    return _registry
