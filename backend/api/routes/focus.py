"""Focus state endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_app_state, get_user_id
from api.errors import error_response

router = APIRouter()


@router.get("/api/focus/state")
async def focus_state(state=Depends(get_app_state), user_id=Depends(get_user_id)):
    try:
        orchestrator = state.get_orchestrator(user_id)
    except ValueError:
        return error_response(401, "INVALID_USER", "Invalid user id")

    context_tool = orchestrator.focus_agent.context_tool
    focus = context_tool.get_focus_state()
    focus["active_window"] = context_tool.get_active_window()
    focus["idle_seconds"] = context_tool.get_idle_seconds()
    return focus
