"""Global application state for FastAPI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from agents.orchestrator import OrchestratorAgent
from tools.idle_watcher import IdleWatcher


@dataclass
class AppState:
    orchestrator: Optional[OrchestratorAgent] = None
    idle_watcher: Optional[IdleWatcher] = None
    event_queue: Optional[asyncio.Queue] = None
    event_loop: Optional[asyncio.AbstractEventLoop] = None


app_state = AppState()
