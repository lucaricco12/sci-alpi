"""A simple, measurements-only summary and explanation for Matthias's group."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from snow_validation import load_observations, project_root


def measured_elevation_summary(observations):
    if observations.duplicated(["station_id", "winter"]).any():
        raise ValueError("Use one measured record per station and winter.")
    if observations.groupby("station_id").elev_m.nunique().gt(1).any():
        raise ValueError("Station elevations must be consistent across winters.")
    means = observations.groupby(["station_id", "period"]).snow_days_30cm.mean().unstack()
    if not {"past", "recent"}.issubset(means) or means[["past", "recent"]].isna().any().any():
        raise ValueError("Both periods are required for every measured station.")
    station = observations.drop_duplicates("station_id")[["station_id", "elev_m"]].merge(
        means.reset_index(), on="station_id", validate="one_to_one")
    station["lost_days"] = station.past - station.recent
    station["elevation_group"] = np.where(station.elev_m.lt(1500), "below_1500m", "at_least_1500m")
    rows = []
    for name in ["all_stations", "below_1500m", "at_least_1500m"]:
        selected = station if name == "all_stations" else station.loc[station.elevation_group.eq(name)]
        if selected.empty:
            raise ValueError(f"No measured stations in {name}.")
        rows.append({"elevation_group": name, "n_stations": len(selected),
                     "days_past": selected.past.mean(), "days_recent": selected.recent.mean(),
                     "lost_days": selected.lost_days.mean(),
                     "min_elevation_m": selected.elev_m.min(), "max_elevation_m": selected.elev_m.max()})
    return pd.DataFrame(rows)


def create_measured_chart(root, summary):
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "text.color":"#263746", "axes.labelcolor":"#263746"})
    chosen = summary.set_index("elevation_group").loc[["below_1500m", "at_least_1500m"]]
    total = summary.loc[summary.elevation_group.eq("all_stations")].iloc[0]
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(2)
    width = .30
    old = ax.bar(x-width/2, chosen.days_past, width, color="#879BA7", label="Older winters: 1986–1995")
    recent = ax.bar(x+width/2, chosen.days_recent, width, color="#16667F", label="Recent winters: 2016–2025")
    for bars in [old, recent]:
        ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=11)
    labels = [f"Below 1,500 m\n{int(chosen.iloc[0].n_stations)} stations",
              f"At least 1,500 m\n{int(chosen.iloc[1].n_stations)} stations"]
    ax.set_xticks(x, labels)
    ax.set_ylabel("Average days per winter with at least 30 cm of snow")
    ax.set_ylim(0, max(chosen.days_past.max(), chosen.days_recent.max())*1.22)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    fig.suptitle("What the real Swiss snow measurements show", x=.1, ha="left", fontsize=16, fontweight="bold", y=.97)
    fig.text(.1, .875, f"Across these {int(total.n_stations)} stations: {total.days_past:.1f} → {total.days_recent:.1f} snow days per winter ({total.lost_days:.1f} fewer days).", fontsize=11)
    fig.text(.1, .055, "MeteoSwiss morning measurements · 1 December–15 April · ten winters in each period", fontsize=9)
    fig.text(.1, .025, "Selected complete station records above 1,000 m; a Swiss subset, not a result for all Alpine ski resorts.", fontsize=9)
    fig.subplots_adjust(left=.1, right=.97, top=.80, bottom=.20)
    output = Path(root)/"docs/figures/snow_measured_before_after.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_method_explanation(root, summary, grid_metrics):
    summary = summary.set_index("elevation_group")
    all_stations = summary.loc["all_stations"]
    low = summary.loc["below_1500m"]
    high = summary.loc["at_least_1500m"]
    grid = grid_metrics.set_index("selection")
    text = f"""# Measured snow summary and location-selection method check

## What are we trying to find out?

We want to count how many days have enough natural snow, then compare older winters with recent winters. For this project, enough snow means at least 30 cm. We count days from 1 December to 15 April.

## What have we done?

1. Collected snow estimates from a computer weather model for the ten-resort pilot.
2. Collected actual snow measurements from 20 Swiss stations.
3. Checked whether the computer estimates agree with the measurements at those stations.
4. Prepared a comparison of older and recent winters using the measurements themselves.

The measurements are readings taken on the ground. The model estimates conditions over larger areas. They are not the same source of information.

## What do the real measurements show?

These are averages for the selected Swiss stations, using 06:00 UTC measurements in winters ending 1986–1995 and 2016–2025.

| Station group | Stations | Older period | Recent period | Fewer snow days |
| --- | ---: | ---: | ---: | ---: |
| All selected stations | {int(all_stations.n_stations)} | {all_stations.days_past:.1f} | {all_stations.days_recent:.1f} | {all_stations.lost_days:.1f} |
| Below 1,500 m | {int(low.n_stations)} | {low.days_past:.1f} | {low.days_recent:.1f} | {low.lost_days:.1f} |
| At least 1,500 m | {int(high.n_stations)} | {high.days_past:.1f} | {high.days_recent:.1f} | {high.lost_days:.1f} |

![Real snow measurements, older and recent winters](figures/snow_measured_before_after.png)

The lower stations in this sample lost more snow days on average. This is a description of these 20 Swiss station records. It does not yet establish what happened in all resorts or in Italy, Austria and France, nor does it prove that elevation caused the difference. The series are not certified homogenised climate records, so site-history changes remain a limitation.

## Why can't we simply use the weather estimates for all resorts?

The matched 400-case check showed that the model counts too many snow days and reproduces little of the measured change between the two periods. A program can run successfully while its input estimates are unsuitable for the conclusion we want to draw.

The follow-up tested one possible explanation: whether choosing the closest weather-model point helps. The test used **all 20 stations and the two existing pilot winters, 1995 and 2025**. It changed only the point-selection setting. The original option overcounted by {grid.loc['land','bias_days']:.1f} days on average; the closest-point option overcounted by {grid.loc['nearest','bias_days']:.1f}. It did not improve this pilot comparison. This is a 40-case sensitivity check, not a new 20-winter climate result.

There is also an altitude limitation. The provider's code does not mark snow depth for elevation correction. Entering a resort's altitude can influence which model point is selected, but does not establish snow depth at that exact height. Therefore the original base-versus-summit test is a point-selection sensitivity check, not a measured comparison of snow at the bottom and top of the resort.

A separate diagnostic queried four already-selected grid points with downscaling disabled (`elevation=nan`) for 1 January 2025. For Davos, the station is at 1,594 m while the API then reports 2,088 m; Weissfluhjoch is at 2,691 m and shares that same returned model point. The retained original responses give identical hourly model snow-depth sequences for those two stations in all 20 study winters. Their actual measured records are different. See `snow_grid_elevation_examples.csv`. This illustrates the spatial/elevation limitation; it is not a complete physical explanation for every model error, and the four illustrative probes are not another climate validation sample.

We have not identified every physical cause of the model errors. These checks rule out an easy fix by choosing the closest point or assuming the altitude parameter adjusts snow depth. A universal subtraction of the average error would not fix the model's different pattern of change.

## What can the group use now?

- A measured result for the 20-station Swiss subset: fewer snow days on average, with a larger average loss at lower stations in this sample.
- A completed data-quality result: the raw weather-model estimates do not reproduce those station changes well.
- Tables, a simple before/after chart, the detailed comparison figures, and a station map.

## What remains for the original four-country study?

The group needs a snow method that works well enough for the four-country comparison, plus a reviewed set of unique resort locations. The 300-row resort file has 293 distinct source URLs and 40 rows flagged for location or identity review. Some sites are valid resorts outside the Alps; other coordinates are clearly suspect. Duplicate ski areas and cross-border areas need an explicit counting rule.

After the snow method and locations are agreed, the remaining work is to expand the download, compare countries and elevations, and connect the snow results to the price and closure analyses. The original four-country conclusions remain open; we have not silently changed the research question to Switzerland alone.

## Where to look

Open `notebooks/03.2_snow_analysis.ipynb` on the pull-request branch and choose Run All. The saved results are already included, so it does not need to download the weather data again. Start with `docs/matthias_simple_explanation.md` for the short explanation. `docs/matthias_next_steps.md` contains the full-panel diagnostics.

## Sources and reproduction

- Measurements: the committed `meteoswiss_station_winters.csv`, originally counted from MeteoSwiss daily files. Parameter `hto000d0`: morning snow depth at 06:00 UTC, in cm. https://opendatadocs.meteoswiss.ch/a-data-groundbased/a5-manual-precipitation-stations
- Weather API: https://open-meteo.com/en/docs/historical-weather-api. The provider documents snow depth in metres and warns about overestimated ERA5-Land snow depth. The project compares 0.30 m to 30 cm.
- Elevation-correction check: `isElevationCorrectable` in the provider's variable definitions, pinned source revision `6d7e23e81efdc4687c06ec4137822d43f9fdda6f`: https://github.com/open-meteo/open-meteo/blob/6d7e23e81efdc4687c06ec4137822d43f9fdda6f/Sources/App/Era5/Era5Variables.swift#L399-L403. It lists temperature-related variables, not snow depth. This supports the limitation above; it does not by itself diagnose every source of snow-model bias.
- `snow_grid_selection_pilot.csv` and `snow_grid_selection_metrics.csv` retain the two-setting comparison. The original 400-case validation is preserved separately. To reproduce missing closest-point pilot responses: `python src/snow_method_check.py`. To rebuild this measured summary and page from saved data: `python src/snow_plain_summary.py`.
"""
    (Path(root)/"docs/snow_method_check.md").write_text(text)


def write_simple_explanation(root, summary):
    rows=summary.set_index("elevation_group")
    low=rows.loc["below_1500m"];high=rows.loc["at_least_1500m"];total=rows.loc["all_stations"]
    text=f"""# Matthias's snow work: the simple version

**Our question:** do ski areas have fewer days with enough natural snow now than before? We define enough snow as at least 30 cm, and compare winters ending in 1986–1995 with those ending in 2016–2025.

There are two sources of snow information: **measurements taken on the ground**, and **estimates from a computer weather model**. We checked whether those estimates agree with the measurements before using them for all the resorts.

## What the real measurements show

| Selected Swiss stations | Average days before | Average days recently | Fewer days |
| --- | ---: | ---: | ---: |
| Below 1,500 m ({int(low.n_stations)} stations) | {low.days_past:.1f} | {low.days_recent:.1f} | {low.lost_days:.1f} |
| At least 1,500 m ({int(high.n_stations)} stations) | {high.days_past:.1f} | {high.days_recent:.1f} | {high.lost_days:.1f} |

Across all {int(total.n_stations)} stations, the average fell from {total.days_past:.1f} to {total.days_recent:.1f} days per winter: **{total.lost_days:.1f} fewer days**. Lower stations in this sample lost more days on average.

![Real measurements before and after](figures/snow_measured_before_after.png)

## Why the computer estimates need more work

The model counts much more snow than the stations measure, and it shows little of their change between the two periods. Choosing the closest model point did not improve our small follow-up test. Entering an altitude also does not automatically give snow depth at that exact height.

**We have a useful result:** the actual station records show fewer snow days in this sample, and the model check reveals an important data-quality limitation. These findings can be presented to the group.

## What comes next

The original project covers four countries. We still need a suitable snow method for that comparison and a reviewed set of resort locations. The current measured result covers **20 selected Swiss stations above 1,000 m**, not all Alpine resorts. Station-history changes remain a limitation; these are not certified homogenised climate records.

The code, tables and charts are prepared. Open `notebooks/03.2_snow_analysis.ipynb` on the pull-request branch and choose Run All to view the saved results. The details and source links are in [the method check](snow_method_check.md) and [the full validation](matthias_next_steps.md).
"""
    (Path(root)/"docs/matthias_simple_explanation.md").write_text(text)


def build_plain_summary(root):
    root=Path(root)
    observations=load_observations(root)
    summary=measured_elevation_summary(observations)
    summary.to_csv(root/"data/processed/snow_measured_elevation_summary.csv", index=False)
    metrics=pd.read_csv(root/"data/processed/snow_grid_selection_metrics.csv")
    create_measured_chart(root,summary)
    write_simple_explanation(root,summary)
    write_method_explanation(root,summary,metrics)
    return summary


if __name__=="__main__":
    root=project_root(Path(__file__).resolve().parent)
    print(build_plain_summary(root).to_string(index=False))
