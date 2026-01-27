"""Error response helpers."""

from __future__ import annotations

from typing import Optional

from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Optional[str] = None,
) -> JSONResponse:
    payload = {"error": True, "code": code, "message": message}
    if detail:
        payload["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)
