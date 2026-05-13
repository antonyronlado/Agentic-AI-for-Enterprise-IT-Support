import asyncio
import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger("nexusdesk.eventbus")


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    async def emit(self, event: str, payload: dict) -> None:
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as exc:
                logger.error("EventBus handler error [%s]: %s", event, exc)


bus = EventBus()
