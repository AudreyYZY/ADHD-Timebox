"""User scoping helpers for per-user storage."""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple


_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_user_id(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = _SAFE_RE.sub("_", raw.strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        return None
    return cleaned[:128]


def user_storage_dirs(user_id: str) -> Tuple[str, str]:
    """Return (brain_dir, memory_dir) for a user."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brain_dir = os.path.join(base_dir, "adhd_brain", "users", user_id)
    memory_dir = os.path.join(brain_dir, "long_term_memory")
    return brain_dir, memory_dir
