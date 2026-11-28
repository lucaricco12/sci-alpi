"""Test the reparse workflow with small fake HTML pages (no network)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import reparse_skiresort as rs  # noqa: E402

PAGE = """
<html><body><h1>Ski resort Test</h1>
<p>For skiing and snowboarding, there are <strong>239 km of slopes</strong> and 15 km of
ski routes available. <strong>46 lifts transport the guests</strong>. The winter sports area is
situated between the elevations of 1,360 and 2,872 m.</p>
<script>var x = "there are 1 km of slopes";</script></body></html>
"""


def test_slug_and_cache_name():
    url = "https://www.skiresort.com/en/ski-resort/ischgl-samnaun-silvretta-arena/"
    assert rs.slug_of(url) == "ischgl-samnaun-silvretta-arena"
    assert rs.cache_path(url, Path("x")).name == "ischgl_samnaun_silvretta_arena.html"


def test_reparse_reads_cached_page_and_reports_missing(tmp_path):
    ok = "https://www.skiresort.com/en/ski-resort/ischgl-samnaun-silvretta-arena/"
    missing = "https://www.skiresort.com/en/ski-resort/not-cached/"
    (tmp_path / rs.cache_path(ok, tmp_path).name).write_text(PAGE, encoding="utf-8")

    table = rs.reparse([ok, missing], html_dir=tmp_path, allow_download=False)

    row = table.set_index("resort_id").loc["ischgl-samnaun-silvretta-arena"]
    assert row["slope_km"] == 239.0 and row["ski_routes_km"] == 15.0 and row["lifts_count"] == 46
    assert row["parse_status"] == "parsed"
    assert table.set_index("resort_id").loc["not-cached", "parse_status"] == "html_missing"
    assert isinstance(table, pd.DataFrame)


def test_script_content_is_ignored(tmp_path):
    url = "https://www.skiresort.com/en/ski-resort/abc/"
    (tmp_path / rs.cache_path(url, tmp_path).name).write_text(PAGE, encoding="utf-8")
    table = rs.reparse([url], html_dir=tmp_path)
    assert table.loc[0, "slope_km"] == 239.0
