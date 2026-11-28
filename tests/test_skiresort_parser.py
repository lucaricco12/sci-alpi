"""Tests for src/skiresort_parser.py.

The sample sentences are copied from the public Skiresort pages (checked on 28 Nov 2026
through search-result excerpts). They are the cases in which the first scraper returned the
ski-routes figure instead of the slope length.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skiresort_parser import normalise_text, parse_skiresort_text, to_number  # noqa: E402

ISCHGL = (
    "For skiing and snowboarding, there are 239 km of slopes and 15 km of ski routes "
    "available. 46 lifts transport the guests. The winter sports area is situated between "
    "the elevations of 1,360 and 2,872 m."
)
SOELDEN = (
    "For skiing and snowboarding, there are 144.1 km of slopes and 8.4 km of ski routes "
    "available. 31 lifts transport the guests. The winter sports area is situated between "
    "the elevations of 1,350 and 3,340 m."
)
ZERMATT = (
    "For skiing and snowboarding, there are 322 km of slopes and 38 km of ski routes "
    "available. 51 lifts transport the guests. The winter sports area is situated between "
    "the elevations of 1,562 and 3,899 m."
)
VALBERG = (
    "For skiing and snowboarding, there are 90 km of slopes available. 23 lifts transport "
    "the guests. The winter sports area is situated between the elevations of 1,412 and 2,020 m."
)
SMALL = (
    "For skiing and snowboarding, there are 3.9 km of slopes available. 3 lifts transport "
    "the guests. The winter sports area is situated between the elevations of 345 and 565 m."
)


def old_scraper_pattern(text):
    """The pattern used in notebook 02.2 before the repair (kept here to show the bug)."""
    m = re.search(r"(?:Ski slopes|Slopes?|Pistes?|Total)[\s\w:]*?(\d+(?:[\.,]\d+)?)\s*km", text, re.I)
    if not m:
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*km\b", text)
    return float(m.group(1).replace(",", ".")) if m else None


@pytest.mark.parametrize(
    "text, slope, routes, lifts, base, top",
    [
        (ISCHGL, 239.0, 15.0, 46, 1360, 2872),
        (SOELDEN, 144.1, 8.4, 31, 1350, 3340),
        (ZERMATT, 322.0, 38.0, 51, 1562, 3899),
        (VALBERG, 90.0, None, 23, 1412, 2020),
        (SMALL, 3.9, None, 3, 345, 565),
    ],
)
def test_sentence_values(text, slope, routes, lifts, base, top):
    result = parse_skiresort_text(text)
    assert result["slope_km"] == slope
    assert result["ski_routes_km"] == routes
    assert result["lifts_count"] == lifts
    assert result["elevation_base_m"] == base
    assert result["elevation_top_m"] == top
    assert result["slope_pattern"] == "sentence"


@pytest.mark.parametrize("text, routes", [(ISCHGL, 15.0), (SOELDEN, 8.4), (ZERMATT, 38.0)])
def test_old_pattern_returned_ski_routes(text, routes):
    """Documents the original error: the old pattern picked the ski-routes number."""
    assert old_scraper_pattern(text) != parse_skiresort_text(text)["slope_km"]


def test_fallback_slope_box():
    text = "Ski slopes » Total: 40.2 km Easy · 19.5 km Ski routes · 8.3 km Ski lifts » Total: 11"
    result = parse_skiresort_text(text)
    assert result["slope_km"] == 40.2
    assert result["slope_pattern"] == "slope_box"
    assert result["ski_routes_km"] == 8.3
    assert result["lifts_count"] == 11


def test_fallback_size_table():
    result = parse_skiresort_text("Slopes · 145.7 km Ski routes · 8.4 km Ski lifts · 31")
    assert result["slope_km"] == 145.7
    assert result["slope_pattern"] == "size_table"


def test_html_like_text_with_separators_and_nbsp():
    text = "there are  239  km of  slopes and 15 km of ski routes available. 1 lift transports the guests."
    result = parse_skiresort_text(text)
    assert result["slope_km"] == 239.0
    assert result["lifts_count"] == 1


def test_nothing_is_guessed():
    result = parse_skiresort_text("A page without the fact box. Distance to the centre 3 km.")
    assert all(value is None for key, value in result.items())


def test_to_number():
    assert to_number("1,360") == 1360.0
    assert to_number("144.1") == 144.1
    assert to_number("") is None
    assert to_number(None) is None


def test_normalise_text_removes_zero_width_space():
    assert normalise_text("Zermatt/​Breuil") == "Zermatt/Breuil"
