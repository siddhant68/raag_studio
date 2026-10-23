"""In-process event bus feeding the SSE endpoint (GET /api/events).

Worker and API threads call `publish()`; every connected browser has an asyncio
queue on its own loop. A small ring buffer lets a reconnecting client replay
what it missed through `Last-Event-ID`.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import threading
from collections import deque
from typing import Any, Optional

RING_SIZE = 200


class Subscriber:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: set[Subscriber] = set()
        self._ring: deque = deque(maxlen=RING_SIZE)
        self._ids = itertools.count(1)

    def publish(self, event: str, data: dict[str, Any]) -> dict:
        with self._lock:
            item = {"id": next(self._ids), "event": event, "data": data}
            self._ring.append(item)
            subs = list(self._subs)
        for sub in subs:
            try:
                sub.loop.call_soon_threadsafe(self._offer, sub, item)
            except RuntimeError:               # that loop is closed: forget the subscriber
                self.unsubscribe(sub)
        return item

    @staticmethod
    def _offer(sub: Subscriber, item: dict) -> None:
        try:
            sub.queue.put_nowait(item)
        except asyncio.QueueFull:              # a stuck client must never block the worker
            pass

    def subscribe(self, loop: asyncio.AbstractEventLoop, last_id: Optional[int] = None) -> tuple[Subscriber, list[dict]]:
        sub = Subscriber(loop)
        with self._lock:
            backlog = [i for i in self._ring if last_id is not None and i["id"] > last_id]
            self._subs.add(sub)
        return sub, backlog

    def unsubscribe(self, sub: Subscriber) -> None:
        with self._lock:
            self._subs.discard(sub)

    def recent(self) -> list[dict]:
        with self._lock:
            return list(self._ring)


def format_sse(item: dict) -> str:
    """One SSE frame: id, event name and a single-line JSON payload."""
    return f"id: {item['id']}\nevent: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
