import ast
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_22 = ROOT / "notebooks" / "02.2_scraping.ipynb"
NOTEBOOK_23 = ROOT / "notebooks" / "02.3_features_spatial.ipynb"


def load_notebook(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


nb22 = load_notebook(NOTEBOOK_22)
nb23 = load_notebook(NOTEBOOK_23)

# Syntax-check every code cell and require a short Markdown explanation before it.
for path, notebook in [(NOTEBOOK_22, nb22), (NOTEBOOK_23, nb23)]:
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            compile(source, f"{path.name}:cell-{index}", "exec")
            assert index > 0 and notebook["cells"][index - 1].get("cell_type") == "markdown", (
                f"{path.name}: code cell {index} must be preceded by a Markdown explanation"
            )

# Execute only pure parser/helper functions from the first 02.2 setup cell.
setup_cell = nb22["cells"][1]
setup_tree = ast.parse("".join(setup_cell["source"]))
function_nodes = [
    node for node in setup_tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {
        "normalise_text", "to_number", "parse_listing_card",
        "extract_villages", "parse_snowmaking_page",
    }
]
namespace = {
    "np": np, "pd": pd, "re": re, "unicodedata": unicodedata,
    "BeautifulSoup": BeautifulSoup,
}
exec(
    compile(ast.Module(body=function_nodes, type_ignores=[]), "02.2_parser_functions", "exec"),
    namespace,
)

parse_card = namespace["parse_listing_card"]
sample_eur = parse_card(
    "KitzSki – Kitzbühel/Kirchberg", "AT",
    "https://www.skiresort.com/en/ski-resort/kitzski/",
    "Test result 1200 m (800 m - 2000 m) 188 km 102 km 66 km 20 km 58 ski lifts € 83,-",
)
assert sample_eur["elevation_base_m"] == 800
assert sample_eur["elevation_top_m"] == 2000
assert sample_eur["slope_km"] == 188
assert sample_eur["lifts_count"] == 58
assert sample_eur["price_day_eur"] == 83

sample_chf = parse_card(
    "Arosa Lenzerheide", "CH",
    "https://www.skiresort.com/en/ski-resort/arosa-lenzerheide/",
    "Test result 1636 m (1229 m - 2865 m) 225 km 110 km 87 km 28 km 43 ski lifts SFr. 89,- / approx. € 94,-",
)
assert sample_chf["price_day_raw"] == 89
assert sample_chf["currency"] == "CHF"
assert sample_chf["price_day_eur"] == 94

snow = namespace["parse_snowmaking_page"](
    "Artificial snow-making 1200 Snow cannons 95 % of the slopes have snow-making capabilities"
)
assert snow["snow_cannons"] == 1200
assert snow["snowmaking_pct"] == 95

# Alpine directory scope must be explicit for the four countries in this project.
setup_source = "".join(nb22["cells"][1]["source"])
scrape_source = "".join(nb22["cells"][3]["source"])
assert '"swiss-alps"' in setup_source
assert '"italian-alps"' in setup_source
assert '"austrian-alps"' in setup_source
assert '"french-alps"' in setup_source
assert 'alpine_scope_verified' in scrape_source
assert 're.fullmatch(r"/en/ski-resort/[^/]+/", parsed_url.path)' in scrape_source

# Spatial workflow uses multiple geocoders and small radius queries, not one broad bbox.
spatial_source = "\n".join("".join(c.get("source", [])) for c in nb23["cells"])
assert "geocode_nominatim" in spatial_source
assert "geocode_photon" in spatial_source
assert "geocode_open_meteo" in spatial_source
overpass_source = "".join(nb23["cells"][7]["source"])
assert "nwr(around:" in overpass_source
assert '["tourism"="hotel"]' in overpass_source
assert '["stars"~"^(4|5)(\\\\.0)?$"]' in overpass_source
assert "OVERPASS_ENDPOINTS" in overpass_source
assert "unavailable" in overpass_source
assert "centroid" not in overpass_source.lower()
assert "proxy" not in overpass_source.lower()

print("PASS: all notebook code cells compile and have Markdown explanations.")
print("PASS: EUR, CHF/EUR and snowmaking parser tests.")
print("PASS: Alpine-only source filters for CH, IT, AT and FR.")
print("PASS: Nominatim, Photon, Open-Meteo and batched Overpass workflow.")
