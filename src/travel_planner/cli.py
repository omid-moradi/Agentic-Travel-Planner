"""Command line entry point.

Phase 1 ships two commands:

``config``   show the effective (secret-free) configuration
``ping``     run one real completion against the configured gateway

The planning commands (``plan``, ``demo``) arrive in phase 2.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence

from travel_planner import __version__
from travel_planner.errors import LLMConfigurationError
from travel_planner.llm import Message, build_llm, describe_provider, system, user


def _cmd_config(args: argparse.Namespace) -> int:
    from travel_planner.config.settings import get_settings

    settings = get_settings()
    payload = {
        "version": __version__,
        "llm": describe_provider(settings),
        "offline_demo_mode": settings.is_offline,
        "has_tavily_key": settings.has_tavily_credentials,
        "default_region": settings.default_region.value,
        "default_language": settings.default_language.value,
        "provider_chains": {
            "hotels": settings.hotels_providers,
            "transport": settings.transport_providers,
            "ride_fare": settings.ride_fare_providers,
            "weather": settings.weather_providers,
        },
        "database_url": settings.database_url.split("@")[-1],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


async def _ping_async(args: argparse.Namespace) -> int:
    try:
        llm = build_llm()
    except LLMConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    messages: list[Message] = [
        system("You are a concise assistant. Answer in one short sentence."),
        user(args.prompt),
    ]
    try:
        result = await llm.complete(messages, max_tokens=args.max_tokens)
    except Exception as exc:
        print(f"error: request failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await llm.aclose()

    print(f"model   : {result.model}")
    print(f"tokens  : {result.usage.total_tokens}")
    print(f"content : {result.content}")
    return 0


def _cmd_ping(args: argparse.Namespace) -> int:
    return asyncio.run(_ping_async(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="travel-planner",
        description="Agentic travel planner for Iran and international trips.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config", help="print the effective configuration (secrets masked)").set_defaults(
        func=_cmd_config
    )

    ping = sub.add_parser("ping", help="send one prompt to the configured model")
    ping.add_argument("prompt", nargs="?", default="Reply with the word: ready")
    ping.add_argument("--max-tokens", type=int, default=128)
    ping.set_defaults(func=_cmd_ping)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
