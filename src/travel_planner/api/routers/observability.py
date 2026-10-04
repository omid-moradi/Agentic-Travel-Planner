"""Metrics endpoint - Prometheus text format."""

from __future__ import annotations

from fastapi import APIRouter, Response

from travel_planner.observability import metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Counters and gauges for scraping (in-process until Redis lands)."""
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4")
