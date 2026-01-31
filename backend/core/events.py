"""Event queue helpers and IdleWatcher integration."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from agents.orchestrator import OrchestratorAgent


def enqueue_event(
    queue: Optional[asyncio.Queue],
    loop: Optional[asyncio.AbstractEventLoop],
    event: Dict[str, Any],
) -> None:
    if queue is None or loop is None:
        return
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is loop:
        queue.put_nowait(event)
    else:
        loop.call_soon_threadsafe(queue.put_nowait, event)


def build_idle_handler(
    orchestrator: OrchestratorAgent,
    event_queue: Optional[asyncio.Queue],
    event_loop: Optional[asyncio.AbstractEventLoop],
):
    def on_idle(payload: Dict[str, Any]) -> None:
        try:
            event_type = payload.get("type", "idle_alert")
            idle_seconds = int(payload.get("idle_seconds") or 0)
            idle_minutes = max(idle_seconds // 60, 1)
            window = payload.get("active_window") or "unknown window"
            focus_state = payload.get("focus_state") if isinstance(payload, dict) else {}
            active_task = (
                focus_state.get("active_task") if isinstance(focus_state, dict) else {}
            )
            task_title = (active_task or {}).get("title") or "current task"

            if event_type == "routine_check":
                message = (
                    f"[ROUTINE_CHECK] Active window: {window}. Active task: {task_title}"
                )
            else:
                message = (
                    f"[IDLE_ALERT] Idle for about {idle_minutes} minutes. "
                    f"Active window: {window}. Active task: {task_title}"
                )

            resp = orchestrator.focus_agent.handle(message)
            content = resp.get("content") if isinstance(resp, dict) else str(resp)
            if "<<SILENCE>>" in content:
                return

            display_content = content.replace("<<SILENCE>>", "").strip()
            if not display_content:
                return

            event = {
                "event": "distraction",
                "data": {
                    "type": event_type,
                    "message": display_content,
                    "task_title": task_title,
                    "window": window,
                },
            }
            enqueue_event(event_queue, event_loop, event)
        except Exception as exc:
            print(f"[IdleWatcher] Failed to push alert: {exc}")

    return on_idle
