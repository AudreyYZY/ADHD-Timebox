"""Idle watcher that fires a callback when the user stays idle for a while."""

import datetime
import threading
import time
from typing import Callable, Dict, Optional

from tools.focus_tools import ContextTool


class IdleWatcher:
    """Polls system idle time and triggers a callback when the user drifts."""

    def __init__(
        self,
        context_tool: Optional[ContextTool] = None,
        on_idle: Optional[Callable[[Dict], None]] = None,
        interval_seconds: int = 30,
        idle_threshold_seconds: int = 300,
        cooldown_seconds: int = 600,
        focus_only: bool = True,
    ):
        self.context_tool = context_tool or ContextTool()
        self.on_idle = on_idle
        self.interval_seconds = interval_seconds
        self.idle_threshold_seconds = idle_threshold_seconds
        self.cooldown_seconds = cooldown_seconds
        self.focus_only = focus_only

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_alert_ts: float = 0.0
        self._warned_idle_unavailable = False

    def start(self):
        """Start the background thread if it is not already running."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="IdleWatcher", daemon=True
        )
        self._thread.start()

    def stop(self):
        """Signal the watcher to stop; the thread exits after the next tick."""
        self._stop_event.set()

    # -- internal -------------------------------------------------------------

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._maybe_fire()
            except Exception as exc:
                print(f"[IdleWatcher] 检测失败：{exc}")
            self._stop_event.wait(self.interval_seconds)

    def _maybe_fire(self):
        idle_seconds = self.context_tool.get_idle_seconds()
        if idle_seconds is None:
            if not self._warned_idle_unavailable:
                print("[IdleWatcher] 无法读取系统空闲时间（可能不是 macOS / ioreg 不可用）。")
                self._warned_idle_unavailable = True
            return

        now_ts = time.time()
        if idle_seconds < self.idle_threshold_seconds:
            return
        if now_ts - self._last_alert_ts < self.cooldown_seconds:
            return

        focus_state = self.context_tool.get_focus_state()
        if self.focus_only:
            if not isinstance(focus_state, dict):
                return
            if focus_state.get("status") != "current":
                return

        active_window = self.context_tool.get_active_window()
        payload = {
            "idle_seconds": idle_seconds,
            "active_window": active_window,
            "focus_state": focus_state,
            "timestamp": datetime.datetime.now().astimezone().isoformat(),
        }

        if self.on_idle:
            try:
                self.on_idle(payload)
            except Exception as exc:
                print(f"[IdleWatcher] on_idle 处理失败：{exc}")

        self._last_alert_ts = now_ts
