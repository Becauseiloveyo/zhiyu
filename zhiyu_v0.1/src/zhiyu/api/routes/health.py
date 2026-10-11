from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from zhiyu import __version__
from zhiyu.core.config import settings
from zhiyu.db.session import get_engine
from zhiyu.services.health import readiness

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "zhiyu-control-plane",
        "version": __version__,
        "architecture_baseline": settings.architecture_baseline,
        "milestone": "v1.0 Stable Prototype",
        "ai_enabled": False,
        "active_security_actions_enabled": False,
        "response_control": "explicit environment policy required",
        "read_only_executors_available": True,
        "verification_enabled": True,
    }


@router.get("/ready")
def ready() -> JSONResponse:
    try:
        result = readiness(get_engine())
    except (SQLAlchemyError, ImportError, ValueError):
        result = {"status": "not_ready", "database": "unavailable", "schema": "unchecked"}
    return JSONResponse(result, status_code=200 if result["status"] == "ready" else 503)
