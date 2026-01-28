"""FastAPI dependencies."""

from __future__ import annotations

from core.state import app_state, AppState


def get_app_state() -> AppState:
    return app_state
