"""Thought parking endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_app_state
from api.errors import error_response

router = APIRouter()


class ParkingRequest(BaseModel):
    message: str
    thought_type: Optional[str] = None


class ParkingResponse(BaseModel):
    content: str
    status: str
    agent: str


@router.post("/api/parking", response_model=ParkingResponse)
async def park_thought(payload: ParkingRequest, state=Depends(get_app_state)):
    if state.orchestrator is None:
        return error_response(503, "SERVICE_NOT_READY", "服务尚未就绪")

    message = (payload.message or "").strip()
    if not message:
        return error_response(400, "INVALID_MESSAGE", "message 不能为空")

    thought_type = (payload.thought_type or "search").strip().lower()
    if thought_type not in {"search", "memo", "todo"}:
        thought_type = "memo"

    parking_service = state.orchestrator.parking_service
    if parking_service._session_id is None:
        parking_service.start_session()

    content = parking_service.dispatch_task(
        content=message,
        task_type=thought_type,
        source="thought_parking",
        run_async=True,
    )

    return ParkingResponse(content=content, status="FINISHED", agent="parking")
