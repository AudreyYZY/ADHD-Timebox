"""Server-Sent Events endpoint."""

from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.dependencies import get_app_state
from api.errors import error_response

router = APIRouter()


def _format_sse(event: Dict[str, Any]) -> str:
    name = event.get("event") or "message"
    data = event.get("data")
    if isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data or {}, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


@router.get("/api/events")
async def sse_events(request: Request, state=Depends(get_app_state)):
    if state.event_queue is None:
        return error_response(503, "SERVICE_NOT_READY", "Event queue not ready")

    heartbeat_interval = 30

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(
                    state.event_queue.get(), timeout=heartbeat_interval
                )
                yield _format_sse(event)
            except asyncio.TimeoutError:
                heartbeat = {
                    "event": "heartbeat",
                    "data": {
                        "timestamp": datetime.datetime.now().astimezone().isoformat()
                    },
                }
                yield _format_sse(heartbeat)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=headers
    )
