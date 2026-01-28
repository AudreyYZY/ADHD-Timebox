"""Focus state endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_app_state
from api.errors import error_response

router = APIRouter()


@router.get("/api/focus/state")
async def focus_state(state=Depends(get_app_state)):
    if state.orchestrator is None:
        return error_response(503, "SERVICE_NOT_READY", "服务尚未就绪")

    context_tool = state.orchestrator.focus_agent.context_tool
    focus = context_tool.get_focus_state()
    focus["active_window"] = context_tool.get_active_window()
    focus["idle_seconds"] = context_tool.get_idle_seconds()
    return focus
