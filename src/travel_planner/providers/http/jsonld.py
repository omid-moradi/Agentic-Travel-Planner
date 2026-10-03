"""JSON-LD / schema.org extraction - the preferred parsing strategy (ADR-006).

Most content sites embed structured ``application/ld+json`` blocks. Parsing those
is dramatically more robust than CSS selectors, so scrapers try this first and
only fall back to structural parsing when the markup is absent.
"""

from __future__ import annotations

import contextlib
import json
import re
from typing import Any

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_jsonld_blocks(html: str) -> list[dict[str, Any]]:
    """Return every parsable JSON-LD object found in the page.

    A malformed block is skipped, never fatal - one bad block must not lose the
    rest of the page's data.
    """
    blocks: list[dict[str, Any]] = []
    for match in _JSONLD_RE.finditer(html):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        blocks.extend(_flatten_jsonld(parsed))
    return blocks


def _flatten_jsonld(node: Any) -> list[dict[str, Any]]:
    """Expand ``@graph`` containers and lists into a flat list of objects."""
    if isinstance(node, list):
        out: list[dict[str, Any]] = []
        for item in node:
            out.extend(_flatten_jsonld(item))
        return out
    if isinstance(node, dict):
        graph = node.get("@graph")
        if isinstance(graph, list):
            out = [item for item in graph if isinstance(item, dict)]
            if not graph and _is_entity(node):
                out = [node]
            return out
        if _is_entity(node):
            return [node]
    return []


def _is_entity(node: dict[str, Any]) -> bool:
    return isinstance(node.get("@type"), (str, list, tuple))


def find_jsonld_by_type(
    html: str, wanted: str | tuple[str, ...]
) -> list[dict[str, Any]]:
    """Return JSON-LD nodes whose ``@type`` matches (case-insensitive).

    ``@type`` may be a string or a list; both are handled.
    """
    if isinstance(wanted, str):
        wanted = (wanted,)
    lowered = {w.lower() for w in wanted}
    results: list[dict[str, Any]] = []
    for block in extract_jsonld_blocks(html):
        types = block.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(t).lower() in lowered for t in types):
            results.append(block)
    return results


def jsonld_to_placeinfo(
    node: dict[str, Any], *, place_type: str, source_name: str
) -> dict[str, Any] | None:
    """Map a schema.org ``TouristAttraction``/``Place``/``Hotel`` to PlaceInfo kwargs.

    Returns ``None`` when the node has no usable name - a record without a name
    is rejected rather than half-parsed (parser contract, ADR-006).
    """
    name = _first_str(node.get("name"))
    if not name:
        return None

    out: dict[str, Any] = {"name": name, "place_type": place_type}

    address = node.get("address")
    if isinstance(address, dict):
        parts = [
            _first_str(address.get(k))
            for k in ("streetAddress", "addressLocality", "addressRegion")
        ]
        out["address"] = ", ".join(p for p in parts if p)
    elif isinstance(address, str):
        out["address"] = address

    geo = node.get("geo")
    if isinstance(geo, dict):
        with contextlib.suppress(TypeError, ValueError):
            out["coordinates"] = {
                "lat": float(geo.get("latitude", 0)),
                "lon": float(geo.get("longitude", 0)),
            }

    description = _first_str(node.get("description"))
    if description:
        out["description"] = description

    url = _first_str(node.get("url"))
    out["source"] = {"name": source_name, "url": url or None}

    return out


def _first_str(value: Any) -> str | None:
    """schema.org fields are sometimes ``{"@value": "..."}`` or ``[...]``."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _first_str(value.get("@value") or value.get("name"))
    if isinstance(value, (list, tuple)) and value:
        return _first_str(value[0])
    return None
