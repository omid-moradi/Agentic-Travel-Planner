"""Tests for the command line interface (offline only)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from travel_planner.cli import build_parser, main
from travel_planner.config.settings import reload_settings
from travel_planner.llm import reset_llm_cache


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_config_command_masks_secrets(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "top-secret-key-value")
    reload_settings()
    assert main(["config"]) == 0
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert "top-secret-key-value" not in json.dumps(payload)
    assert payload["llm"]["has_api_key"] is True
    assert "provider_chains" in payload


def test_config_command_reports_offline_mode(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    reload_settings()
    assert main(["config"]) == 0
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert payload["offline_demo_mode"] is True
    assert payload["llm"]["offline"] is True


def test_ping_in_mock_mode_makes_no_network_call(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    reload_settings()
    reset_llm_cache()
    assert main(["ping", "hello"]) == 0
    out = capsys.readouterr().out
    assert "content :" in out
    assert "hello" in out


def test_ping_without_credentials_exits_with_code_2(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "apmix")
    monkeypatch.setenv("LLM_API_KEY", "")
    reload_settings()
    assert main(["ping", "hello"]) == 2
    assert "LLM_API_KEY" in capsys.readouterr().err
    reload_settings()
