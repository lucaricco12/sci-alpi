"""Parse the fact box of a Skiresort page (text version).

Why this file exists
--------------------
The first scraper (notebook 02.2) took the *first* number followed by "km" near the word
"Slopes". On many pages the text is

    "For skiing and snowboarding, there are 239 km of slopes and 15 km of ski routes
     available. 46 lifts transport the guests. The winter sports area is situated
     between the elevations of 1,360 and 2,872 m."

and the old pattern returned the ski-routes figure (15 km instead of 239 km). The same
happened for Soelden (8.4 instead of 144.1) and Zermatt (38 instead of 322). The lift count
was never captured (empty column, later filled with an artefact).

This module reads the sentence itself and returns the three numbers separately.
It works on plain text, so it can be tested without a network connection.
"""

from __future__ import annotations

import re
import unicodedata

NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"


def to_number(text: str | None) -> float | None:
    """Convert '1,360' -> 1360.0 and '144.1' -> 144.1. Return None for empty input."""
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    # A comma followed by exactly three digits is a thousands separator in the English pages.
    cleaned = re.sub(r",(?=\d{3}\b)", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalise_text(text: str) -> str:
    """Unicode-normalise and collapse all white space (also non-breaking spaces)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def _first(patterns: list[str], text: str) -> list[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return list(match.groups())
    return None


def parse_skiresort_text(text: str) -> dict:
    """Return slope length, ski routes, lifts and the elevation range from one page text.

    Keys: slope_km, ski_routes_km, lifts_count, elevation_base_m, elevation_top_m,
    slope_pattern (which rule matched; useful for the audit).
    Missing values are None. Nothing is guessed.
    """
    t = normalise_text(text)
    result = {
        "slope_km": None,
        "ski_routes_km": None,
        "lifts_count": None,
        "elevation_base_m": None,
        "elevation_top_m": None,
        "slope_pattern": None,
    }

    # 1) Main sentence on the page.
    groups = _first([rf"there (?:are|is) {NUMBER} km of slopes"], t)
    if groups:
        result["slope_km"] = to_number(groups[0])
        result["slope_pattern"] = "sentence"
    else:
        # 2) The 'Ski slopes' box:  "Ski slopes » Total: 40.2 km"
        groups = _first([rf"ski slopes\s*»?\s*total:?\s*{NUMBER}\s*km"], t)
        if groups:
            result["slope_km"] = to_number(groups[0])
            result["slope_pattern"] = "slope_box"
        else:
            # 3) The size table:  "Slopes · 239 km"
            groups = _first([rf"\bslopes\s*[·|:]\s*{NUMBER}\s*km"], t)
            if groups:
                result["slope_km"] = to_number(groups[0])
                result["slope_pattern"] = "size_table"

    groups = _first(
        [
            rf"{NUMBER} km of ski routes",
            rf"ski routes\s*[·|:]\s*{NUMBER}\s*km",
        ],
        t,
    )
    if groups:
        result["ski_routes_km"] = to_number(groups[0])

    groups = _first(
        [
            r"(\d+) lifts? transports? the guests",
            r"ski lifts\s*»?\s*total:?\s*(\d+)",
        ],
        t,
    )
    if groups:
        result["lifts_count"] = int(groups[0])

    groups = _first([rf"between the elevations of {NUMBER} and {NUMBER} m"], t)
    if groups:
        low, high = to_number(groups[0]), to_number(groups[1])
        if low is not None and high is not None and low < high:
            result["elevation_base_m"], result["elevation_top_m"] = int(low), int(high)

    return result
