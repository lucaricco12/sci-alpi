"""Rebuild both Matthias checkpoints from saved inputs, without API calls."""
from pathlib import Path

from checkpoint_database import build_crosswalk, update_checkpoint_database
from snow_checkpoint_figures import make_figures
from snow_checkpoint_map import build_map
from snow_checkpoint_models import run_models
from snow_checkpoint_report import write_report
from snow_validation import project_root


def main():
    root = project_root(Path(__file__).resolve().parent)
    results = run_models(root)
    make_figures(root, results)
    map_result = build_map(root)
    crosswalk = build_crosswalk(root)
    joins = update_checkpoint_database(root, crosswalk)
    write_report(root, results, map_result, joins)
    print(results["regression_metrics"][["model_id", "n_reference_sites", "r_squared", "adjusted_r_squared", "rmse_5fold_days"]].round(3).to_string(index=False))
    print(map_result["coverage"].to_string(index=False))
    print(joins.to_string(index=False))
    print("Ready: notebooks/03.3_matthias_checkpoints.ipynb; docs/matthias_checkpoint_report.md; docs/ski_resorts_closures_map.html")
    print("Measured claims remain Swiss-only; the four-country model sample is exploratory and does not validate resort risk.")


if __name__ == "__main__":
    main()
