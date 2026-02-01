"""Thought parking endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_app_state, get_user_id
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
async def park_thought(
    payload: ParkingRequest,
    state=Depends(get_app_state),
    user_id=Depends(get_user_id),
):
    try:
        orchestrator = state.get_orchestrator(user_id)
    except ValueError:
        return error_response(401, "INVALID_USER", "Invalid user id")

    message = (payload.message or "").strip()
    if not message:
        return error_response(400, "INVALID_MESSAGE", "message cannot be empty")

    thought_type = (payload.thought_type or "search").strip().lower()
    if thought_type not in {"search", "memo", "todo"}:
        thought_type = "memo"

    parking_service = orchestrator.parking_service
    if parking_service._session_id is None:
        parking_service.start_session()

    content = parking_service.dispatch_task(
        content=message,
        task_type=thought_type,
        source="thought_parking",
        run_async=True,
    )

    return ParkingResponse(content=content, status="FINISHED", agent="parking")
