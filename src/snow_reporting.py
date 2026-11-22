"""Figures and input review for the matched snow validation notebook."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from snow_validation import compute_results

OBSERVED, MODEL = "#16667F", "#CB6638"


def audit_resorts(root):
    """Preserve every source row. Flags request review, not automatic exclusion."""
    frame = pd.read_csv(Path(root) / "data/processed/resorts_features.csv")
    if not {"url", "country", "latitude", "longitude", "resort_name"}.issubset(frame):
        raise ValueError("Resort features must include source URLs, countries and coordinates.")
    audit = frame[["resort_name", "country", "url", "elevation_base_m", "elevation_top_m", "latitude", "longitude"]].copy()
    audit.insert(0, "source_csv_row", np.arange(len(audit)) + 2)
    audit["resort_id"] = audit.url.str.rstrip("/").str.rsplit("/", n=1).str[-1]
    audit["duplicate_url"] = audit.url.duplicated(keep=False)
    country_counts = audit.groupby("url").country.nunique()
    audit["cross_border_url"] = audit.url.map(country_counts).gt(1)
    audit["outside_alpine_screening_box"] = ~audit.latitude.between(43, 49) | ~audit.longitude.between(4, 17)
    audit["missing_coordinates"] = audit[["latitude", "longitude"]].isna().any(axis=1)
    audit["invalid_elevation_range"] = ~(audit.elevation_base_m.ge(0) & audit.elevation_top_m.gt(audit.elevation_base_m))
    audit["missing_lifts"] = frame.lifts_count.isna()
    audit["missing_source_price"] = frame.price_day_raw.isna()
    cache_path = Path(root) / "data/processed/resorts_geocoded_cache.csv"
    cached = pd.read_csv(cache_path)
    if len(cached) != len(frame) or not cached.resort_name.equals(frame.resort_name):
        raise ValueError("Geocoding cache rows no longer align with features; review the cache join.")
    audit["cache_coordinate_differs"] = ~(np.isclose(frame.latitude, cached.latitude) & np.isclose(frame.longitude, cached.longitude))
    flags = ["duplicate_url", "cross_border_url", "outside_alpine_screening_box", "missing_coordinates", "invalid_elevation_range", "cache_coordinate_differs"]
    audit["review_reasons"] = ["; ".join(c for c in flags if row[c]) for _, row in audit.iterrows()]
    audit["requires_location_or_identity_review"] = audit[flags].any(axis=1)
    audit.to_csv(Path(root) / "data/processed/snow_resort_input_review.csv", index=False)
    return audit


def save_figure(fig, destination):
    fig.savefig(destination, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def create_figures(root, pairs, changes):
    root = Path(root)
    destination = root / "docs/figures"
    destination.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#263746", "text.color": "#263746"})
    metrics, _, trend = compute_results(pairs)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 7), sharex=True, sharey=True)
    for ax, period, label in zip(axes, ["past", "recent"], ["Winters ending 1986–1995", "Winters ending 2016–2025"]):
        data = pairs.loc[pairs.period.eq(period)]
        row = metrics.loc[metrics.period.eq(period)].iloc[0]
        ax.scatter(data.observed_days_06utc, data.model_days_06utc, s=25, color=OBSERVED, alpha=0.5, edgecolors="none")
        ax.plot([0, 140], [0, 140], color="#84929C", lw=1.2, ls="--")
        ax.set(xlim=(-3, 141), ylim=(-3, 141), xlabel="MeteoSwiss snow days at 06:00 UTC")
        ax.set_title(f"{label}\n{len(data)} matched station winters · r = {row.pearson_r:.2f}\nBias {row.bias_days:+.1f} days · RMSE {row.rmse_days:.1f} days", fontsize=10, pad=10)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=.12)
    axes[0].set_ylabel("ERA5-Land snow days at 06:00 UTC")
    fig.suptitle("Do modelled snow-day counts match measured snow?", fontsize=15, fontweight="bold")
    fig.text(.5, .04, f"{pairs.station_id.nunique()} Swiss stations above 1,000 m · Dec 1–Apr 15 · depth ≥30 cm · dashed line: perfect agreement", ha="center", fontsize=9)
    fig.subplots_adjust(left=.08, right=.98, bottom=.16, top=.75, wspace=.2)
    save_figure(fig, destination / "snow_validation_counts.png")

    data = changes.sort_values("observed_lost_days")
    fig, ax = plt.subplots(figsize=(11, 8))
    y = np.arange(len(data))
    ax.barh(y+.18, data.observed_lost_days, height=.34, color=OBSERVED, label="MeteoSwiss measurements")
    ax.barh(y-.18, data.model_lost_days, height=.34, color=MODEL, label="ERA5-Land model")
    ax.set_yticks(y, [f"{r.station_name} ({int(r.elev_m):,} m)" for r in data.itertuples()])
    ax.axvline(0, color="#84929C", lw=1)
    ax.set_xlabel("Past-period mean minus recent-period mean (snow days per winter)")
    ax.set_title("Does the model reproduce the change between periods?", loc="left", fontsize=15, fontweight="bold", pad=40)
    ax.text(0, 1.025, f"Positive = fewer recent snow days. Means: observed {trend.mean_observed_lost_days.iloc[0]:+.1f}, model {trend.mean_model_lost_days.iloc[0]:+.1f} days.", transform=ax.transAxes, fontsize=10)
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=.15)
    fig.tight_layout()
    save_figure(fig, destination / "snow_validation_changes.png")

    geometry = json.loads((root / "data/processed/alpine_map_boundaries.geojson").read_text())
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for feature in geometry["features"]:
        geom = feature["geometry"]
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for polygon in polygons:
            ax.add_patch(Polygon(polygon[0], facecolor="#EDF1F0", edgecolor="#B4C0C5", linewidth=.7))
    locations = pairs.drop_duplicates(["station_id", "grid_lat", "grid_lon"])
    for r in locations.itertuples():
        ax.plot([r.lon, r.grid_lon], [r.lat, r.grid_lat], color=MODEL, lw=.8, alpha=.6, zorder=3)
    ax.scatter(locations.grid_lon, locations.grid_lat, facecolors="none", edgecolors=MODEL, s=42, label="Returned model-grid location", zorder=4)
    ax.scatter(locations.lon, locations.lat, c=OBSERVED, s=25, label="MeteoSwiss station", zorder=5)
    offsets = {"DAV":(6,-14), "WFJ":(6,5), "GAD":(-25,8), "GTT":(6,5), "GRH":(-28,-12), "SIA":(-25,-15), "BIV":(-25,6)}
    for r in locations.itertuples():
        ax.annotate(r.station_id, (r.lon,r.lat), xytext=offsets.get(r.station_id,(5,5)), textcoords="offset points", fontsize=9, zorder=6)
    ax.set(xlim=(6.65,10.65), ylim=(45.8,47.25), xlabel="Longitude (° E)", ylabel="Latitude (° N)")
    ax.set_aspect(1/np.cos(np.radians(46.5)))
    ax.set_title("Validation stations and their returned weather-model grid points", loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="lower left", fontsize=9, framealpha=.95)
    fig.text(.5,.015,"Station coordinates: MeteoSwiss · ERA5-Land via Open-Meteo · country boundaries: Natural Earth (public domain)",ha="center",fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1))
    save_figure(fig, destination / "snow_validation_stations_map.png")

    pilot = pd.read_csv(root / "data/processed/snow_summary_10resorts.csv").sort_values("lost_snow_days")
    fig, ax = plt.subplots(figsize=(10,6))
    ax.barh(pilot.name, pilot.lost_snow_days, color=MODEL)
    ax.axvline(0, color="#84929C", lw=1)
    for i,r in enumerate(pilot.itertuples()):
        ax.text(r.lost_snow_days + (.2 if r.lost_snow_days>=0 else -.2), i, f"{r.lost_snow_days:+.1f}", va="center", ha="left" if r.lost_snow_days>=0 else "right", fontsize=9)
    ax.set_xlim(pilot.lost_snow_days.min()-3,pilot.lost_snow_days.max()+3)
    ax.set_xlabel("Past-period mean minus recent-period mean (modelled snow days per winter)")
    ax.set_title("Original 10-location pilot: modelled change", loc="left", fontsize=15, fontweight="bold", pad=14)
    ax.grid(axis="x",alpha=.15)
    fig.text(.5,.015,"Daily maximum ≥30 cm · base-town reference points · pilot only; model bias and input limitations apply",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1))
    save_figure(fig, destination / "snow_pilot_period_change.png")


def write_findings(root, pairs, audit):
    root=Path(root)
    metrics,changes,trend=compute_results(pairs)
    overall=metrics.loc[metrics.period.eq("all")].iloc[0]
    trend=trend.iloc[0]
    countries=audit.country.value_counts().to_dict()
    n=len(audit); unique=audit.url.nunique()
    examples=[]
    for prefix in ["Les 3 Vallées", "4 Vallées"]:
        selection=audit.loc[audit.resort_name.str.startswith(prefix) & audit.outside_alpine_screening_box]
        if not selection.empty:
            row=selection.iloc[0]
            examples.append(f"{prefix} at approximately {row.latitude:.2f}°, {row.longitude:.2f}°")
    examples_text="Examples needing review include " + "; ".join(examples) + ". " if examples else ""
    text=f"""# Matthias: snow validation and next steps

## Completed on 22 November 2026

The next notebook is `notebooks/03.2_snow_analysis.ipynb`. Run All reads committed results, recalculates the comparison and recreates the figures without downloading data. The optional download switch refreshes model seasons with a cache.

For the short explanation and the measurements-only before/after chart, start with `docs/matthias_simple_explanation.md`. A follow-up location-selection test and its sources are in `docs/snow_method_check.md`. That 40-case sensitivity check is separate from the full 400-case benchmark reported below.

### SQ2: compare like with like

We queried ERA5-Land at each of the {pairs.station_id.nunique()} MeteoSwiss station coordinates, requesting the station elevation. Both sources use the same {len(pairs)} station–winter keys, the same dates (1 December–15 April), and the same observation time (06:00 UTC). The threshold is 0.30 m in the model and 30 cm in the measurements. All model hourly seasons were checked for exact timestamps, finite non-negative depth and complete coverage before counting. Returned grid coordinates and response hashes are retained.

The primary validation indicator uses the **06:00 reading**, matching MeteoSwiss `hto000d0`. The resort pilot uses the **daily maximum**; these are different indicators. The station-model table includes both so the effect can be inspected rather than hidden.

| Diagnostic | Result |
| --- | ---: |
| Matched station winters | {len(pairs)} |
| Mean model minus observed count | {overall.bias_days:+.2f} days/winter |
| Mean absolute error | {overall.mae_days:.2f} days/winter |
| Root mean squared error | {overall.rmse_days:.2f} days/winter |
| Pooled count correlation (descriptive) | {overall.pearson_r:.3f} |
| Mean observed loss, past minus recent | {trend.mean_observed_lost_days:+.2f} days/winter |
| Mean modelled loss, past minus recent | {trend.mean_model_lost_days:+.2f} days/winter |
| Correlation of the 20 station-specific changes | {trend.loss_pearson_r:.3f} |
| Nominal Pearson p-value for changes | {trend.loss_pearson_p_nominal:.4g} |
| Stations agreeing on the direction of change | {int(trend.same_direction_stations)}/{len(changes)} |
| Extra model days from daily maximum instead of 06:00 | {overall.mean_daily_max_extra_days:.2f} days/winter |
| Model seasons counted as snow-covered every day | {overall.model_full_season_fraction:.1%} |
| Measured seasons counted as snow-covered every day | {overall.observed_full_season_fraction:.1%} |

In this panel, the model counts an average of {overall.bias_days:+.1f} days more than the measurements. The measured past-to-recent loss is {trend.mean_observed_lost_days:.1f} days per winter, compared with {trend.mean_model_lost_days:.1f} in the model. Using the daily maximum instead of the morning reading changes the model count by only {overall.mean_daily_max_extra_days:.2f} days on average. Thus the timing difference alone does not account for the measured/model discrepancy in this run. A complete season has 136 or 137 days.

Bias is model minus observation. A positive loss means fewer days in the recent decade. RMSE is in snow days per winter. Correlation describes association and does not establish agreement. A large positive bias cannot be dismissed because correlation is positive. Compare the bias, error, changes and scatterplots together before applying the 100-day rule to model estimates.

The 400 winters repeat 20 stations. We do not treat them as 400 independent stations for significance testing. The change correlation uses one value per station (n=20); its p-value is nominal and assumes independent stations, an approximation given spatial dependence. It is exploratory evidence. These observations are an unhomogenised manual-station subset above 1,000 m; site histories and representativeness must be checked before climate attribution or extrapolation to all four countries and lower-altitude resorts. MeteoSwiss recommends homogeneous series for long-term climate analyses.

### Expanded resort inputs need review before bulk downloading

The source feature file contains {n} rows but {unique} distinct source URLs: {n-unique} excess duplicate entries, across {int(audit.loc[audit.duplicate_url,'url'].nunique())} URL groups. {int(audit.loc[audit.cross_border_url,'url'].nunique())} groups occur under multiple countries. Current row counts are {countries}; they are not exactly 75 per country after the upstream country corrections.

The automatic audit preserves all {n} input rows. {int(audit.outside_alpine_screening_box.sum())} rows lie outside the broad screening rectangle 43–49° N, 4–17° E. This flags possible geocoding errors or legitimate resorts outside the intended Alpine scope. Passing the rectangle does not prove Alpine membership or validate a base-area coordinate. {examples_text}Inspect `snow_resort_input_review.csv`.

The feature and geocoding-cache coordinates differ for {int(audit.cache_coordinate_differs.sum())} row(s) (the original audit includes the upstream Portes du Soleil correction). Lift counts are missing in {int(audit.missing_lifts.sum())} rows. Source prices are missing in {int(audit.missing_source_price.sum())} rows although their converted-price column has filled values. These are input provenance issues, not evidence of zero lifts or observed prices. The notebook does not overwrite Lorenzo's source or feature CSVs.

### How to finish Matthias's part

1. Review the matched validation and decide whether raw ERA5-Land counts are suitable for the research question. Open-Meteo explicitly warns about overestimated ERA5-Land snow depth and limited spatial resolution. Do not subtract the aggregate validation bias from every resort as a universal correction. A calibrated method would need independent or held-out evaluation.
2. Agree with Lorenzo on a unique ski-area key (the canonical source URL), an explicit rule for cross-border systems, the Alpine sample boundary, and verified base-area coordinates. Deduplicate ski areas for overall climate summaries. Cross-border areas need a separate category or exclusion from country-specific comparisons unless explicitly modelled as distinct gateways. Preserve their separate price-market records for later pricing analysis if needed.
3. After inputs and indicator are agreed, download the 20 study winters for each approved location. A 300-row file is not yet a 300-area climate sample. Keep rate limits, cache responses, check completeness and publish `snow_winters.csv` only when every approved resort has all 20 winters. The existing `03_snow_pilot.ipynb` supports an approved `data/raw/resorts_full_input.csv`, but that input has not been created from unreviewed coordinates.
4. Create the full-sample period-change chart, country/elevation comparison and map. For SQ1 use one period difference per unique resort, inspect country/elevation coverage, and use ANOVA/regression only after checking sample quality and assumptions. The 10-location pilot is descriptive and cannot establish country-wide conclusions.
5. Hand over the validated snow table, source decisions, figures and limitations for Luca's price/affordability/closure joins and the final slides.

### Outputs

- `station_model_winters.csv`: {len(pairs)} validated model seasons, with 06:00 and daily-maximum counts, returned grid points, request URLs and response SHA-256 hashes.
- `snow_station_validation.csv`: one-to-one joined measured/model station winters and count errors.
- `snow_validation_metrics.csv`: bias, MAE, RMSE, descriptive r, saturation and daily-maximum sensitivity by period.
- `snow_station_changes.csv`: the two period means and their differences for each station.
- `snow_validation_trend_metrics.csv`: n=20 station-change diagnostics, including the nominal p-value.
- `snow_resort_input_review.csv`: review flags for all original feature-file rows.
- `docs/figures/`: count-agreement figure, station-change figure, station/grid map and explicitly labelled original-pilot chart.

### Reproduce

From the repository root, install `requirements.txt`, open `notebooks/03.2_snow_analysis.ipynb`, select the Python environment and Run All. The added notebook defaults to the saved tables. To refresh all missing raw station-model seasons: `python src/snow_validation.py --download`. API calls start at most once every 0.6 seconds across three workers, and a 429 response stops the batch; successful caches remain reusable. Existing published model tables are preserved if any season fails. API HTTP failures are not converted into zero snow days.

### Sources

- Open-Meteo Historical Weather API, hourly `snow_depth`, `models=era5_land`, UTC, land cell selection: https://open-meteo.com/en/docs/historical-weather-api (accessed 22 November 2026). ECMWF/Copernicus ERA5-Land via Open-Meteo, CC BY 4.0. The grid coordinates can differ from the requested station location; the map shows this explicitly.
- MeteoSwiss manual precipitation/snow network: https://opendatadocs.meteoswiss.ch/a-data-groundbased/a5-manual-precipitation-stations. Parameter metadata specifies `hto000d0` as morning snow depth at 06:00 UTC, in centimetres: https://data.geo.admin.ch/ch.meteoschweiz.ogd-nime/ogd-nime_meta_parameters.csv. The existing 400-row observation panel was retained and rechecked for complete seasons.
- Natural Earth country boundaries, public domain: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson. A seven-country subset is committed for offline map reproduction. Terms: https://www.naturalearthdata.com/about/terms-of-use/.
"""
    (root / "docs/matthias_next_steps.md").write_text(text)


def build_report(root, pairs):
    _, changes, _ = compute_results(pairs)
    audit = audit_resorts(root)
    create_figures(root, pairs, changes)
    write_findings(root, pairs, audit)
    return audit
