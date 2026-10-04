"""Exports: ICS calendar and PDF - both generated deterministically, LLM-free.

ICS is a standard RFC 5545 calendar file the user can import into any
calendar app. The PDF is a minimal, hand-rolled single-page writer (no heavy
dependency): it produces a real, valid PDF with one page of text lines - a
full typesetting pipeline arrives when the design exists.
"""

from __future__ import annotations

import textwrap

from travel_planner.schemas import DayPlan
from travel_planner.schemas import Itinerary as ItineraryModel


def _escape_ics(value: str) -> str:
    """RFC 5545 text escaping."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _hhmm_to_hm(value: str) -> tuple[int, int]:
    hours, minutes = value.split(":")
    return int(hours), int(minutes)


def itinerary_to_ics(itinerary: ItineraryModel, *, title: str) -> str:
    """Build an RFC 5545 calendar with one all-day event per trip day."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Agentic Travel Planner//EN",
        "CALSCALE:GREGORIAN",
    ]
    for day in itinerary.days:
        # All-day events: DTSTART;VALUE=DATE and no DTEND means one day.
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:day-{day.day_number}-{day.date.isoformat()}@travel-planner",
                f"DTSTAMP:{day.date.isoformat().replace('-', '')}T090000Z",
                f"DTSTART;VALUE=DATE:{day.date.isoformat().replace('-', '')}",
                f"SUMMARY:{_escape_ics(f'{title} - Day {day.day_number}: {day.city}')}",
                f"DESCRIPTION:{_escape_ics(_day_description(day))}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _day_description(day: DayPlan) -> str:
    parts = [f"{len(day.activities)} activities in {day.city}."]
    for activity in day.activities:
        parts.append(f"{activity.start_time}-{activity.end_time} {activity.place.name}")
    if day.daily_budget is not None:
        parts.append(f"Budget: {day.daily_budget.amount:,.0f} {day.daily_budget.currency.value}")
    return " ".join(parts)


# ----------------------------------------------------------------------- pdf
def _pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width) or [""]


def itinerary_to_pdf(itinerary: ItineraryModel, *, title: str) -> bytes:
    """A minimal valid one-page PDF with the trip summary.

    Hand-rolled on purpose: no dependency, correct xref offsets, and the
    output opens in every reader. Persian text is included as-is; a proper
    shaping/embedding pipeline arrives with the designed export (recorded in
    STATUS-P7.md).
    """
    page_width, page_height = 595, 842  # A4 in points
    margin = 48
    line_height = 14
    max_width = 78  # characters per line for Helvetica 10pt

    lines: list[str] = [title, ""]
    for day in itinerary.days:
        lines.append(f"Day {day.day_number} - {day.city} ({day.date.isoformat()})")
        for activity in day.activities:
            lines.append(
                f"  {activity.start_time}-{activity.end_time}  {activity.place.name}"
            )
        if day.daily_budget is not None:
            lines.append(
                f"  Budget: {day.daily_budget.amount:,.0f} {day.daily_budget.currency.value}"
            )
        lines.append("")

    if itinerary.total_cost is not None:
        lines.append(
            f"Total (estimated): {itinerary.total_cost.amount:,.0f} "
            f"{itinerary.total_cost.currency.value}"
        )
    lines.append("Prices are estimates and may differ on the provider's site.")

    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap(line, max_width))

    # Content stream: move down the page line by line.
    content_parts = [
        "BT",
        "/F1 10 Tf",
        f"{margin} {page_height - margin} Td",
        f"{line_height} TL",
    ]
    for index, line in enumerate(wrapped):
        prefix = "" if index == 0 else "T*"
        content_parts.append(f"{prefix} ({_pdf_escape(line)}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ).encode(),
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        5: b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    }

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode()
        out += objects[number]
        out += b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for number in range(1, len(objects) + 1):
        out += f"{offsets[number]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


__all__ = ["itinerary_to_ics", "itinerary_to_pdf"]
