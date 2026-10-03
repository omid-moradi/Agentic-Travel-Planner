"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from travel_planner import __version__
from travel_planner.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    """Liveness: the process answers."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready() -> dict[str, object]:
    """Readiness: liveness plus the effective configuration summary."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "offline": settings.is_offline,
        "region": settings.default_region.value,
    }
