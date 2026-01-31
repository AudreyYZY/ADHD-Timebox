"""OAuth endpoints for Google via OpenOnion."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.dependencies import get_app_state
from api.errors import error_response
from core.oauth import OAuthError, apply_google_oauth, init_google_oauth, poll_google_status

router = APIRouter()


def _google_status_payload() -> Dict[str, Any]:
    access = os.getenv("GOOGLE_ACCESS_TOKEN")
    refresh = os.getenv("GOOGLE_REFRESH_TOKEN")
    scopes = os.getenv("GOOGLE_SCOPES", "")
    email = os.getenv("GOOGLE_EMAIL", "")
    expires_at = os.getenv("GOOGLE_TOKEN_EXPIRES_AT", "")

    if not access or not refresh:
        return {
            "connected": False,
            "message": "Click \"Connect Google Calendar\" to authorize.",
        }

    try:
        from connectonion import GoogleCalendar

        _ = GoogleCalendar()
    except Exception as exc:
        return {
            "connected": False,
            "message": "Google Calendar is not authorized or unavailable.",
            "detail": str(exc),
        }

    return {
        "connected": True,
        "email": email or None,
        "scopes": scopes or None,
        "expires_at": expires_at or None,
    }


@router.get("/api/auth/status")
async def auth_status():
    return {"google": _google_status_payload()}


@router.post("/api/auth/google")
async def auth_google():
    try:
        data = init_google_oauth()
    except OAuthError as exc:
        return error_response(502, "OAUTH_INIT_FAILED", "OAuth init failed", str(exc))

    auth_url = data.get("auth_url") or data.get("url")
    if not auth_url:
        return error_response(502, "OAUTH_INIT_FAILED", "No authorization URL returned")

    return {
        "auth_url": auth_url,
        "poll_endpoint": "/api/auth/google/status",
        "timeout_seconds": 300,
    }


@router.get("/api/auth/google/status")
async def auth_google_status(state=Depends(get_app_state)):
    try:
        status = poll_google_status()
    except OAuthError as exc:
        return error_response(502, "OAUTH_STATUS_FAILED", "OAuth status fetch failed", str(exc))

    status_text = status.get("status")
    connected = bool(status.get("connected")) or status_text == "connected"

    if not connected:
        if status_text in {"failed", "timeout"}:
            return {
                "status": "failed",
                "message": status.get("message") or "Authorization timed out. Please retry.",
            }
        return {
            "status": "pending",
            "message": status.get("message") or "Waiting for browser authorization...",
        }

    if state.orchestrator is None:
        return error_response(503, "SERVICE_NOT_READY", "Service not ready")

    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    env_path = os.path.abspath(env_path)

    try:
        creds = apply_google_oauth(state.orchestrator, env_path)
    except OAuthError as exc:
        return error_response(502, "OAUTH_CREDENTIALS_FAILED", "Failed to fetch credentials", str(exc))
    except Exception as exc:
        return error_response(500, "OAUTH_APPLY_FAILED", "Failed to apply Google credentials", str(exc))

    return {
        "status": "connected",
        "email": creds.get("google_email") or creds.get("email"),
        "message": "Google account connected",
    }
