"""Tests for structured logging and secret redaction."""

from __future__ import annotations

import json
import logging

from travel_planner.config.settings import AppEnvironment, LogFormat, Settings
from travel_planner.logging_config import REDACTED, configure_logging, get_logger, redact


def _settings(fmt: LogFormat = LogFormat.JSON) -> Settings:
    return Settings(_env_file=None, log_format=fmt, app_env=AppEnvironment.TEST)  # type: ignore[call-arg]


class TestRedaction:
    def test_secret_keys_are_masked(self) -> None:
        assert redact("sk_live_abc", key="api_key") == REDACTED
        assert redact("x", key="Authorization") == REDACTED
        assert redact("x", key="webhook_secret") == REDACTED

    def test_emails_are_masked(self) -> None:
        assert "user@example.com" not in str(redact("contact user@example.com now"))

    def test_long_digit_runs_are_masked(self) -> None:
        masked = str(redact("national id 123456789012345678"))
        assert "123456789012345678" not in masked

    def test_short_numbers_survive(self) -> None:
        assert redact("cost 1250000 toman") == "cost 1250000 toman"

    def test_nested_structures_are_walked(self) -> None:
        payload = {"outer": {"api_key": "secret", "note": "call 1234567890123"}}
        masked = redact(payload)
        assert masked["outer"]["api_key"] == REDACTED
        assert "1234567890123" not in masked["outer"]["note"]

    def test_lists_are_walked(self) -> None:
        masked = redact(["a@b.com", "1234567890123456"])
        assert "a@b.com" not in masked[0]
        assert "1234567890123456" not in masked[1]


class TestFormatters:
    def test_json_output_is_one_object_per_line(self, capsys) -> None:  # type: ignore[no-untyped-def]
        configure_logging(_settings(LogFormat.JSON), force=True)
        logger = get_logger("travel_planner.test")
        logger.info("hello %s", "world")
        line = capsys.readouterr().out.strip()
        payload = json.loads(line)
        assert payload["message"] == "hello world"
        assert payload["level"] == "INFO"

    def test_json_context_is_redacted(self, capsys) -> None:  # type: ignore[no-untyped-def]
        configure_logging(_settings(LogFormat.JSON), force=True)
        logger = get_logger("travel_planner.test")
        logger.info("call", extra={"context": {"api_key": "sk_live_x", "ok": True}})
        payload = json.loads(capsys.readouterr().out.strip())
        assert payload["context"]["api_key"] == REDACTED
        assert payload["context"]["ok"] is True

    def test_console_output_is_readable(self, capsys) -> None:  # type: ignore[no-untyped-def]
        configure_logging(_settings(LogFormat.CONSOLE), force=True)
        get_logger("travel_planner.test").warning("careful")
        assert "careful" in capsys.readouterr().out

    def test_third_party_loggers_are_quieted(self) -> None:
        configure_logging(_settings(), force=True)
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("openai").level == logging.WARNING

    def test_configure_logging_does_not_duplicate_its_own_handler(self) -> None:
        root = logging.getLogger()
        before = len(root.handlers)
        configure_logging(_settings(), force=False)
        configure_logging(_settings(), force=False)
        # pytest installs its own capture handlers, so compare against that baseline.
        assert len(root.handlers) == before

    def test_force_replaces_existing_handlers(self) -> None:
        root = logging.getLogger()
        before = len(root.handlers)
        configure_logging(_settings(), force=True)
        assert len(root.handlers) == 1
        configure_logging(_settings(), force=True)
        assert len(root.handlers) == 1
        assert before >= 1
