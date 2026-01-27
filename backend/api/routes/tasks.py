"""Task list and updates."""

from __future__ import annotations

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import get_app_state
from api.errors import error_response
from core.events import enqueue_event
from tools.reward_tools import RewardToolkit

router = APIRouter()


class TaskStatusUpdate(BaseModel):
    status: str


def _format_time(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if "T" in text:
        text = text.replace("T", " ")
    if " " in text:
        return text.split(" ", 1)[1]
    return text


def _normalize_task(task: dict) -> dict:
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "start": _format_time(task.get("start")),
        "end": _format_time(task.get("end")),
        "type": task.get("type", "work"),
        "status": task.get("status", "pending"),
        "google_event_id": task.get("google_event_id"),
    }


@router.get("/api/tasks")
async def list_tasks(date: Optional[str] = Query(None), state=Depends(get_app_state)):
    if state.orchestrator is None:
        return error_response(503, "SERVICE_NOT_READY", "服务尚未就绪")

    today = datetime.date.today()
    plan_manager = state.orchestrator.plan_manager
    plan_date, date_err = plan_manager._parse_plan_date(date, today)
    if date_err:
        return error_response(400, "INVALID_DATE", "日期格式错误", date_err)

    tasks, path, err = plan_manager._load_tasks(plan_date.isoformat(), False)
    if err:
        return error_response(404, "PLAN_NOT_FOUND", "未找到计划文件", err)

    tasks = tasks or []
    normalized = [_normalize_task(t) for t in tasks if isinstance(t, dict)]
    done = len(
        [
            t
            for t in normalized
            if str(t.get("status", "")).lower() in {"done", "completed", "complete"}
        ]
    )
    summary = {"total": len(normalized), "done": done, "pending": len(normalized) - done}

    return {"date": plan_date.isoformat(), "tasks": normalized, "summary": summary}


@router.patch("/api/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: TaskStatusUpdate,
    date: Optional[str] = Query(None),
    state=Depends(get_app_state),
):
    if state.orchestrator is None:
        return error_response(503, "SERVICE_NOT_READY", "服务尚未就绪")

    if not payload.status:
        return error_response(400, "INVALID_STATUS", "status 不能为空")

    plan_manager = state.orchestrator.plan_manager
    today = datetime.date.today()
    plan_date, date_err = plan_manager._parse_plan_date(date, today)
    if date_err:
        return error_response(400, "INVALID_DATE", "日期格式错误", date_err)

    tasks, path, err = plan_manager._load_tasks(plan_date.isoformat(), False)
    if err:
        return error_response(404, "PLAN_NOT_FOUND", "未找到计划文件", err)
    if tasks is None:
        return error_response(500, "PLAN_INVALID", "计划文件格式异常", path)

    target = plan_manager._find_task(tasks, task_id)
    if not target:
        return error_response(404, "TASK_NOT_FOUND", "未找到任务", task_id)

    status = payload.status.strip().lower()
    target["status"] = status
    if status in {"done", "completed", "complete"}:
        target["completed_at"] = datetime.datetime.now().astimezone().isoformat()

    write_err = plan_manager._write_tasks(path, tasks)
    if write_err:
        return error_response(500, "WRITE_FAILED", "写入失败", write_err)

    reward = None
    if status in {"done", "completed", "complete"}:
        toolkit = state.orchestrator.reward_agent.toolkit
        try:
            reward = toolkit.generate_micro_reward(target.get("title") or task_id)
        except Exception:
            reward = RewardToolkit().generate_micro_reward(
                target.get("title") or task_id
            )

        enqueue_event(
            state.event_queue,
            state.event_loop,
            {
                "event": "task_completed",
                "data": {"task_id": target.get("id") or task_id, "reward": reward},
            },
        )

    return {"success": True, "task": _normalize_task(target), "reward": reward}
