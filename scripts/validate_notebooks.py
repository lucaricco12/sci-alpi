import ast
import json
import re
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_22 = ROOT / "notebooks" / "02.2_scraping.ipynb"
NOTEBOOK_23 = ROOT / "notebooks" / "02.3_features_spatial.ipynb"


def load_notebook(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


nb22 = load_notebook(NOTEBOOK_22)
nb23 = load_notebook(NOTEBOOK_23)

# Syntax-check every code cell without running network requests.
for path, notebook in [(NOTEBOOK_22, nb22), (NOTEBOOK_23, nb23)]:
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            compile(source, f"{path.name}:cell-{index}", "exec")

# Execute only the definitions and deterministic parser tests from 02.2.
setup_cell = next(
    cell for cell in nb22["cells"]
    if cell.get("cell_type") == "code"
    and "def parse_listing_card" in "".join(cell.get("source", []))
)
setup_tree = ast.parse("".join(setup_cell["source"]))
function_nodes = [
    node for node in setup_tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"normalise_text", "to_number", "parse_listing_card"}
]
namespace = {"np": np, "re": re, "unicodedata": unicodedata}
exec(compile(ast.Module(body=function_nodes, type_ignores=[]), "02.2_parser_functions", "exec"), namespace)
smoke_cell = next(
    cell for cell in nb22["cells"]
    if cell.get("cell_type") == "code"
    and "Parser smoke tests based on the format" in "".join(cell.get("source", []))
)
exec("".join(smoke_cell["source"]), namespace)

# Ensure the Overpass request is validly quoted and filters both 4- and 5-star hotels.
overpass_cell = next(
    cell for cell in nb23["cells"]
    if cell.get("cell_type") == "code"
    and "OVERPASS_QUERY =" in "".join(cell.get("source", []))
)
overpass_source = "".join(overpass_cell["source"])
assert 'node["tourism"="hotel"]' in overpass_source
assert 'way["tourism"="hotel"]' in overpass_source
assert 'relation["tourism"="hotel"]' in overpass_source
assert r'["stars"~"^(4|5)(\.0)?$"]' in overpass_source
assert 'out center tags;' in overpass_source
assert r'\"tourism\"' not in overpass_source

# pandas nullable string assignment must work with the NumPy 2 runtime used in CI.
hotel_counts = pd.Series([0.0, np.nan], dtype="float64")
hotel_source = pd.Series(pd.NA, index=hotel_counts.index, dtype="string")
hotel_source.loc[hotel_counts.notna()] = "OpenStreetMap Overpass"
assert hotel_source.iloc[0] == "OpenStreetMap Overpass"
assert pd.isna(hotel_source.iloc[1])

print("PASS: all notebook code cells compile.")
print("PASS: EUR and CHF/EUR Skiresort parser smoke tests.")
print("PASS: Overpass query quoting, hotel types and star filter.")
