"""Server-Sent Events (SSE) broadcaster for streaming pipeline progress."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict


class EventBroadcaster:
    """Manages real-time SSE progress events for runs."""

    def __init__(self) -> None:
        self._queues: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        if run_id in self._queues and q in self._queues[run_id]:
            self._queues[run_id].remove(q)

    async def broadcast(self, run_id: str, stage: str, message: str, payload: Dict[str, Any] | None = None) -> None:
        event_data = {
            "run_id": run_id,
            "stage": stage,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload or {},
        }
        if run_id in self._queues:
            for q in self._queues[run_id]:
                await q.put(event_data)


broadcaster = EventBroadcaster()


async def sse_event_generator(run_id: str) -> AsyncGenerator[str, None]:
    """Generates SSE formatted string messages."""
    q = broadcaster.subscribe(run_id)
    try:
        # Initial greeting event
        init_event = {
            "run_id": run_id,
            "stage": "connected",
            "message": "Connected to CleanSlate pipeline event stream",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"data: {json.dumps(init_event)}\n\n"

        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                # Keep-alive heartbeat comment
                yield ": keep-alive\n\n"
    finally:
        broadcaster.unsubscribe(run_id, q)
