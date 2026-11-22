"""Rebuild Matthias's saved results in one command, without network requests."""
from pathlib import Path

import pandas as pd

from resort_review import build_roster
from snow_candidates import compare_candidates
from snow_method_check import compare_selections
from snow_plain_summary import build_plain_summary
from snow_reporting import build_report
from snow_validation import export_results, load_observations, pair_sources, project_root


def main():
    root = project_root(Path(__file__).resolve().parent)
    observations = load_observations(root)
    models = pd.read_csv(root / "data/processed/station_model_winters.csv")
    pairs = pair_sources(observations, models)
    export_results(root, pairs)
    compare_selections(root, pd.read_csv(root / "data/processed/station_model_nearest_pilot.csv"))
    build_report(root, pairs)
    roster = build_roster(root)
    cases, metrics = compare_candidates(root, pd.read_csv(root / "data/processed/station_model_candidates.csv"))
    cases.to_csv(root / "data/processed/snow_candidate_validation.csv", index=False)
    metrics.to_csv(root / "data/processed/snow_candidate_metrics.csv", index=False)
    summary = build_plain_summary(root)
    print(summary[["elevation_group", "n_stations", "days_past", "days_recent", "lost_days"]].round(1).to_string(index=False))
    print(f"\nResort roster: {len(roster)} distinct areas; {int(roster.include_in_alpine_candidate_set.sum())} Alpine candidates.")
    print("Open notebooks/03.2_snow_analysis.ipynb for tables and charts, or docs/matthias_simple_explanation.md for the short explanation.")
    print("Four-country snow conclusions remain pending a suitable full-period snow method and location review.")


if __name__ == "__main__":
    main()
