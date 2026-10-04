"""Lightweight observability: OTLP-compatible spans and Prometheus metrics.

Deliberately dependency-free:

* **Spans** follow the OpenTelemetry data model (trace_id, span_id, name,
  start/end unix timestamps, attributes, status) and are emitted through the
  structured logger - an OTLP exporter can subscribe to the same records
  later without touching callers.
* **Metrics** are counters/gauges exposed in Prometheus text format at
  ``/api/v1/metrics``. Every number is in-process unless Redis arrives
  (documented in STATUS-P8.md).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_TRACE_HEADER = 16  # bytes -> 32 hex chars
_SPAN_HEADER = 8  # bytes -> 16 hex chars


def _hex(n_bytes: int) -> str:
    return random.randbytes(n_bytes).hex()


@dataclass(slots=True)
class Span:
    """One traced operation, in the OpenTelemetry data-model shape."""

    trace_id: str
    span_id: str
    name: str
    start_time_unix_nano: int
    end_time_unix_nano: int
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"

    def duration_ms(self) -> float:
        return (self.end_time_unix_nano - self.start_time_unix_nano) / 1_000_000


class Tracer:
    """Emits OTLP-shaped spans through the structured logger."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _current_trace(self) -> str:
        trace = getattr(self._local, "trace_id", None)
        if trace is None:
            trace = _hex(_TRACE_HEADER)
            self._local.trace_id = trace
        return trace

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        """Trace one operation; exceptions mark the span failed and re-raise."""
        start = time.time_ns()
        span = Span(
            trace_id=self._current_trace(),
            span_id=_hex(_SPAN_HEADER),
            name=name,
            start_time_unix_nano=start,
            end_time_unix_nano=start,
            attributes=dict(attributes),
        )
        try:
            yield span
            span.status = "ok"
        except Exception as exc:
            span.status = "error"
            span.attributes["error"] = type(exc).__name__
            raise
        finally:
            span.end_time_unix_nano = time.time_ns()
            logger.info(
                "span %s -> %s (%.1fms)",
                span.name,
                span.status,
                span.duration_ms(),
                extra={
                    "context": {
                        "trace_id": span.trace_id,
                        "span_id": span.span_id,
                        "span": {
                            "name": span.name,
                            "status": span.status,
                            "duration_ms": round(span.duration_ms(), 2),
                            **span.attributes,
                        },
                    }
                },
            )


#: The process-wide tracer.
tracer = Tracer()


# ------------------------------------------------------------------- metrics
class MetricsRegistry:
    """Thread-safe counters and gauges in Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._created_at = time.time()

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Increment a labelled counter."""
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> str:
        if not labels:
            return name
        suffix = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{suffix}}}"

    def render(self) -> str:
        """The registry as Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            for key, value in sorted(self._counters.items()):
                lines.append(f"{key} {value}")
            for key, value in sorted(self._gauges.items()):
                lines.append(f"{key} {value}")
        lines.append(f"metrics_uptime_seconds {time.time() - self._created_at:.1f}")
        return "\n".join(lines) + "\n"


#: The process-wide metrics registry.
metrics = MetricsRegistry()
