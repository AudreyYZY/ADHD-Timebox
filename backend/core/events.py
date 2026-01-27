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
            window = payload.get("active_window") or "未知窗口"
            focus_state = payload.get("focus_state") if isinstance(payload, dict) else {}
            active_task = (
                focus_state.get("active_task") if isinstance(focus_state, dict) else {}
            )
            task_title = (active_task or {}).get("title") or "当前任务"

            if event_type == "routine_check":
                message = f"[ROUTINE_CHECK] 当前窗口：{window}。当前任务：{task_title}"
            else:
                message = (
                    f"[IDLE_ALERT] 已空闲约 {idle_minutes} 分钟。"
                    f"当前窗口：{window}。当前任务：{task_title}"
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
            print(f"[IdleWatcher] 推送提醒失败：{exc}")

    return on_idle
