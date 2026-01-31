"""Global application state for FastAPI."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

from agents.orchestrator import OrchestratorAgent
from core.plan_manager import PlanManagerWithLock
from core.users import normalize_user_id, user_storage_dirs
from tools.idle_watcher import IdleWatcher


@dataclass
class AppState:
    orchestrator: Optional[OrchestratorAgent] = None
    orchestrators: Dict[str, OrchestratorAgent] = field(default_factory=dict)
    idle_watcher: Optional[IdleWatcher] = None
    event_queue: Optional[asyncio.Queue] = None
    event_queues: Dict[str, asyncio.Queue] = field(default_factory=dict)
    event_loop: Optional[asyncio.AbstractEventLoop] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_orchestrator(self, user_id: str) -> OrchestratorAgent:
        safe_id = normalize_user_id(user_id)
        if not safe_id:
            raise ValueError("Invalid user id")
        with self._lock:
            orchestrator = self.orchestrators.get(safe_id)
            if orchestrator:
                return orchestrator
            brain_dir, memory_dir = user_storage_dirs(safe_id)
            plan_manager = PlanManagerWithLock(plan_dir=brain_dir)
            orchestrator = OrchestratorAgent(
                plan_manager=plan_manager, memory_dir=memory_dir, brain_dir=brain_dir
            )
            self.orchestrators[safe_id] = orchestrator
            return orchestrator

    def get_event_queue(self, user_id: str) -> asyncio.Queue:
        safe_id = normalize_user_id(user_id)
        if not safe_id:
            raise ValueError("Invalid user id")
        with self._lock:
            queue = self.event_queues.get(safe_id)
            if queue is None:
                queue = asyncio.Queue()
                self.event_queues[safe_id] = queue
            return queue


app_state = AppState()
