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
        routine_check_seconds: int = 300,  # proactive context check every 5 minutes
    ):
        self.context_tool = context_tool or ContextTool()
        self.on_idle = on_idle
        self.interval_seconds = interval_seconds
        self.idle_threshold_seconds = idle_threshold_seconds
        self.cooldown_seconds = cooldown_seconds
        self.focus_only = focus_only
        self.routine_check_seconds = routine_check_seconds

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_alert_ts: float = 0.0
        self._last_routine_check_ts: float = time.time()
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
                print(f"[IdleWatcher] Check failed: {exc}")
            self._stop_event.wait(self.interval_seconds)

    def _maybe_fire(self):
        now_ts = time.time()
        
        # 1) Routine context check (covers "active distraction")
        if self.routine_check_seconds > 0:
            if now_ts - self._last_routine_check_ts >= self.routine_check_seconds:
                self._fire_event("routine_check", 0)
                self._last_routine_check_ts = now_ts
                # Routine check does not affect idle alert cooldown

        # 2) Idle alert - user inactive
        idle_seconds = self.context_tool.get_idle_seconds()
        if idle_seconds is None:
            if not self._warned_idle_unavailable:
                print(
                    "[IdleWatcher] Unable to read system idle time (not macOS or ioreg unavailable)."
                )
                self._warned_idle_unavailable = True
            return

        if idle_seconds < self.idle_threshold_seconds:
            return
        if now_ts - self._last_alert_ts < self.cooldown_seconds:
            return

        self._fire_event("idle_alert", idle_seconds)
        self._last_alert_ts = now_ts

    def _fire_event(self, event_type: str, idle_seconds: int):
        focus_state = self.context_tool.get_focus_state()
        if self.focus_only:
            if not isinstance(focus_state, dict):
                return
            if focus_state.get("status") != "current":
                # If not in focus mode, do not interrupt.
                print(
                    f"\n[IdleWatcher] Idle for {idle_seconds}s, but not in focus mode "
                    f"(Status={focus_state.get('status')}); skipping."
                )
                return

        active_window = self.context_tool.get_active_window()
        payload = {
            "type": event_type,  # idle_alert or routine_check
            "idle_seconds": idle_seconds,
            "active_window": active_window,
            "focus_state": focus_state,
            "timestamp": datetime.datetime.now().astimezone().isoformat(),
        }

        if self.on_idle:
            try:
                self.on_idle(payload)
            except Exception as exc:
                print(f"[IdleWatcher] on_idle failed: {exc}")
