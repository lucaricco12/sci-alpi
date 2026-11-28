"""Re-read the cached Skiresort pages with the corrected parser.

Usage (run in the Codespace, from the repository root):

    python src/reparse_skiresort.py                # only uses pages already on disk
    python src/reparse_skiresort.py --download     # also downloads the missing pages (slow, polite)

Input : data/processed/resorts_clean.csv (column url) and the cached HTML pages in
        data/raw/html_resorts/  (the folder is not on GitHub, it lives in the Codespace of the
        person who ran notebook 02.2).
Output: data/processed/skiresort_reparsed.csv  (one row per resort_id)

Only slope length, ski routes, lift count and the elevation range are read. Prices are NOT
re-read, because a new download could show a different date's price.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skiresort_parser import parse_skiresort_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW_HTML = ROOT / "data" / "raw" / "html_resorts"
OUT = PROCESSED / "skiresort_reparsed.csv"

USER_AGENT = "ZHAW-AlpineSkiResearch-StudentProject/1.0 (course project; student contact via ZHAW)"


def slug_of(url: str) -> str:
    """Last part of the Skiresort URL, e.g. 'ischgl-samnaun-silvretta-arena'."""
    return [part for part in str(url).split("/") if part][-1]


def cache_path(url: str, html_dir: Path = RAW_HTML) -> Path:
    """File name used by notebook 02.2 for the cached page."""
    name = re.sub(r"[^a-z0-9]+", "_", slug_of(url).lower())[:60]
    return html_dir / f"{name}.html"


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ")


def download(url: str, target: Path) -> bool:
    import requests

    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    except requests.RequestException as error:
        print(f"  download failed for {url}: {error}")
        return False
    if response.status_code != 200 or len(response.text) < 2000:
        print(f"  download failed for {url}: HTTP {response.status_code}")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(response.text, encoding="utf-8")
    return True


def reparse(urls: list[str], html_dir: Path = RAW_HTML, allow_download: bool = False,
            delay_s: float = 3.0) -> pd.DataFrame:
    rows = []
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for url in urls:
        path = cache_path(url, html_dir)
        status = "parsed"
        if not path.exists() and allow_download:
            time.sleep(delay_s)
            if download(url, path):
                status = "parsed_after_download"
        if not path.exists():
            rows.append({"resort_id": slug_of(url), "url": url, "parse_status": "html_missing"})
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_skiresort_text(html_to_text(html))
        parsed.update(
            {
                "resort_id": slug_of(url),
                "url": url,
                "parse_status": status if parsed["slope_km"] is not None else "slope_not_found",
                "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                "parsed_utc": stamp,
            }
        )
        rows.append(parsed)
    columns = [
        "resort_id", "url", "slope_km", "ski_routes_km", "lifts_count",
        "elevation_base_m", "elevation_top_m", "slope_pattern", "parse_status",
        "html_sha256", "parsed_utc",
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--download", action="store_true", help="download pages that are not cached")
    parser.add_argument("--delay", type=float, default=3.0, help="seconds between downloads")
    parser.add_argument("--html-dir", type=Path, default=RAW_HTML)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    clean = pd.read_csv(PROCESSED / "resorts_clean.csv")
    urls = sorted(clean["url"].dropna().unique())
    print(f"{len(urls)} resort pages to read; cache folder: {args.html_dir}")
    table = reparse(urls, args.html_dir, args.download, args.delay)
    table.to_csv(args.out, index=False)

    counts = table["parse_status"].value_counts().to_dict()
    print("Result:", counts)
    ok = table["slope_km"].notna().sum()
    print(f"Slope length found for {ok} of {len(table)} resorts -> {args.out.relative_to(ROOT)}")
    if ok < len(table):
        print("Missing pages: run again with --download, or copy data/raw/html_resorts from the "
              "Codespace that ran notebook 02.2.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
