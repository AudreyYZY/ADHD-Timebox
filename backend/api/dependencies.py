"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request, HTTPException

from core.state import app_state, AppState
from core.users import normalize_user_id


def get_app_state() -> AppState:
    return app_state


def get_user_id(request: Request) -> str:
    raw = request.headers.get("x-user-id") or request.headers.get("x-user")
    user_id = normalize_user_id(raw)
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing or invalid user id")
    return user_id
