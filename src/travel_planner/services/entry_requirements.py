"""Entry requirements - advisory only, never asserted as certain (ADR-009).

The master prompt is explicit: never state visa rules as certain without a
dated source. Every requirement here is ``inferred`` until a sourced
requirements provider (phase 3 chain) is wired in; the payload always carries
the verify-with-official-source warning, and the UI must render it.
"""

from __future__ import annotations

from travel_planner.db.models import Trip
from travel_planner.schemas import DataStatus


def entry_requirements(trip: Trip) -> dict[str, object]:
    """Advisory entry requirements for the trip's region.

    For domestic Iran travel this is trivially the national ID. For
    international trips the items are labelled ``inferred``: they are the
    universally true concerns (passport validity, visa, insurance) and the
    caller is always warned to verify with the official source.
    """
    warning = (
        "These entry requirements are advisory and may be out of date. Always "
        "verify with the destination's official government source before travel."
    )

    if trip.region == "iran":
        return {
            "status": DataStatus.INFERRED.value,
            "items": [
                {
                    "requirement": "National ID card",
                    "detail": "Domestic travel within Iran requires a national ID card.",
                    "status": DataStatus.CONFIRMED.value,
                }
            ],
            "warning": warning,
        }

    return {
        "status": DataStatus.INFERRED.value,
        "items": [
            {
                "requirement": "Passport validity",
                "detail": (
                    "Many destinations require the passport to be valid for at least "
                    "6 months beyond the planned departure date."
                ),
                "status": DataStatus.INFERRED.value,
            },
            {
                "requirement": "Visa / entry permit",
                "detail": (
                    "Visa rules depend on your nationality and the destination. Check "
                    "the destination's official e-visa portal for the current rules."
                ),
                "status": DataStatus.INFERRED.value,
            },
            {
                "requirement": "Travel health insurance",
                "detail": "Insurance covering the whole stay is required by many countries at the border.",
                "status": DataStatus.INFERRED.value,
            },
            {
                "requirement": "Return/onward ticket",
                "detail": "Some destinations ask for proof of onward travel at check-in or the border.",
                "status": DataStatus.INFERRED.value,
            },
        ],
        "warning": warning,
    }
