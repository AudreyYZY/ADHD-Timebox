"""Thread-safe PlanManager wrapper."""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from tools.plan_tools_v2 import PlanManager


class PlanManagerWithLock(PlanManager):
    """PlanManager with a file lock for JSON read/write."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_lock = threading.Lock()

    def _write_tasks(self, path: str, tasks: List[Dict]) -> Optional[str]:
        with self._file_lock:
            return super()._write_tasks(path, tasks)

    def _load_tasks(
        self, target_date: str, create_if_missing: bool
    ) -> Tuple[Optional[List[Dict]], str, Optional[str]]:
        with self._file_lock:
            return super()._load_tasks(target_date, create_if_missing)
