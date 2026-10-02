"""Structured logging setup.

Rules enforced here:

* never log secrets - :func:`redact` masks anything that looks like a credential
* never log PII - emails and long digit runs are masked in user-facing logs
* one JSON object per line in production, human-readable on a terminal
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

from travel_planner.config.settings import LogFormat, Settings, get_settings

#: Keys whose values must never appear in a log line.
SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credit_card",
        "password",
        "secret",
        "session",
        "token",
        "webhook_secret",
    }
)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_DIGITS = re.compile(r"\b\d{9,}\b")

REDACTED = "***redacted***"


def redact(value: Any, *, key: str | None = None) -> Any:
    """Mask secrets and obvious PII in a value about to be logged."""
    if key is not None and key.lower() in SENSITIVE_KEYS:
        return REDACTED
    if isinstance(value, str):
        masked = _EMAIL.sub("***email***", value)
        return _LONG_DIGITS.sub("***digits***", masked)
    if isinstance(value, dict):
        return {k: redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with secrets and PII already masked."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = redact(context)
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Readable output for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        context = getattr(record, "context", None)
        if isinstance(context, dict) and context:
            base = f"{base} | {json.dumps(redact(context), ensure_ascii=False, default=str)}"
        return base


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Install the root handler. Safe to call repeatedly."""
    cfg = settings or get_settings()
    root = logging.getLogger()
    if root.handlers and not force:
        return

    handler = logging.StreamHandler(sys.stdout)
    if cfg.log_format is LogFormat.JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            ConsoleFormatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s", "%H:%M:%S")
        )
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(cfg.log_level.upper())

    # Third-party loggers are noisy at INFO and can echo request URLs.
    for noisy in ("httpx", "httpcore", "openai", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that always has a handler, even before configuration."""
    logger = logging.getLogger(name)
    if not logging.getLogger().handlers:
        configure_logging(force=True)
    return logger
