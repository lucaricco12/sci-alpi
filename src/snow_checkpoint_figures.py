"""Exploratory and diagnostic figures with measured/model scope labels."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from snow_checkpoint_models import design_matrix

COUNTRY_COLORS = {"CH": "#C23B3B", "IT": "#2A8C68", "AT": "#3875A8", "FR": "#BF7A24"}
BANDS = ["below_1500m", "1500_to_below_2000m", "at_least_2000m"]
BAND_LABELS = ["Below 1,500 m", "1,500–<2,000 m", "At least 2,000 m"]


def save(fig, root, name, footer):
    fig.text(.06, .025, footer, ha="left", fontsize=8.5, color="#52626C")
    fig.tight_layout(rect=(.02, .06, .99, .92))
    fig.savefig(Path(root) / "docs/figures" / name, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_figures(root, results):
    root = Path(root)
    (root / "docs/figures").mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "text.color": "#263746", "axes.labelcolor": "#263746"})
    measured = results["measured_data"]
    model = results["model_data"]
    fit = results["measured_fit"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    ax = axes[0, 0]
    ax.hist(measured.observed_lost_days, bins=7, color="#16667F", edgecolor="white")
    ax.axvline(0, color="#84929C", ls="--")
    ax.set(title="Distribution of measured snow-day losses", xlabel="Past mean − recent mean (days/winter)", ylabel="Number of stations")
    ax = axes[0, 1]
    data = [measured.loc[measured.elevation_band.eq(b), "observed_lost_days"] for b in BANDS]
    ax.boxplot(data, tick_labels=[f"{label}\nn={len(d)}" for label, d in zip(BAND_LABELS, data)], patch_artist=True,
               boxprops={"facecolor": "#B9D4DC"}, medianprops={"color": "#16667F"})
    ax.axhline(0, color="#84929C", ls="--", lw=1)
    ax.set(title="Losses by station elevation", ylabel="Measured loss (days/winter)")
    ax = axes[1, 0]
    x = np.linspace(measured.elev_m.min(), measured.elev_m.max(), 100)
    frame = pd.DataFrame({"elev_m": x})
    interval = fit.get_prediction(design_matrix(frame, "elev_m")).summary_frame()
    ax.scatter(measured.elev_m, measured.observed_lost_days, color="#16667F", s=35)
    ax.plot(x, interval["mean"], color="#16667F")
    ax.fill_between(x, interval.mean_ci_lower, interval.mean_ci_upper, color="#16667F", alpha=.15)
    ax.axhline(0, color="#84929C", ls="--", lw=1)
    ax.set(title=f"Elevation association · R² = {fit.rsquared:.2f}", xlabel="Station elevation (m)", ylabel="Measured loss (days/winter)")
    ax = axes[1, 1]
    ax.scatter(measured.observed_days_past, measured.observed_days_recent, color="#16667F", s=35)
    ax.plot([0, 140], [0, 140], color="#84929C", ls="--")
    ax.set(xlim=(0, 140), ylim=(0, 140), title="Past versus recent snow reliability", xlabel="Older-period mean (days/winter)", ylabel="Recent-period mean (days/winter)")
    for ax in axes.flat:
        ax.grid(alpha=.13)
    fig.suptitle("Measured snow: 20 selected Swiss stations", x=.06, ha="left", fontsize=16, fontweight="bold")
    save(fig, root, "checkpoint_measured_eda.png", "MeteoSwiss · ≥30 cm at 06:00 UTC · Dec 1–Apr 15 · winters 1986–1995 / 2016–2025\nPositive loss = fewer recent snow days. Selected stations >1,000 m; unhomogenised records, not an all-Alps estimate.")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    countries = ["CH", "IT", "AT", "FR"]
    ax = axes[0, 0]
    values = [model.loc[model.country.eq(c), "lost_snow_days"] for c in countries]
    boxes = ax.boxplot(values, tick_labels=[f"{c}\nn={len(v)}" for c, v in zip(countries, values)], patch_artist=True)
    for box, c in zip(boxes["boxes"], countries):
        box.set_facecolor(COUNTRY_COLORS[c]); box.set_alpha(.4)
    ax.axhline(0, color="#84929C", ls="--", lw=1)
    ax.set(title="Modelled losses by country", ylabel="Modelled loss (days/winter)")
    ax = axes[0, 1]
    for c in countries:
        selected = model.loc[model.country.eq(c)]
        ax.scatter(selected.elev_base_m, selected.lost_snow_days, label=c, color=COUNTRY_COLORS[c], s=35)
        # Draw only within each country's observed elevation range.
        line = pd.DataFrame({"elev_base_m": np.linspace(selected.elev_base_m.min(), selected.elev_base_m.max(), 60), "country": c})
        prediction = results["model_fits"]["sq1_model_country_elevation_interaction"].predict(
            design_matrix(line, "elev_base_m", include_country=True, interaction=True))
        ax.plot(line.elev_base_m, prediction, color=COUNTRY_COLORS[c], alpha=.7)
    ax.axhline(0, color="#84929C", ls="--", lw=1)
    ax.set(title="Country-specific elevation slopes", xlabel="Source-listed base elevation (m)", ylabel="Modelled loss (days/winter)")
    ax.legend(frameon=False, ncol=2)
    ax = axes[1, 0]
    corr = model[["elev_base_m", "days_past", "days_recent", "lost_snow_days"]].corr()
    image = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    labels = ["Base height", "Past days", "Recent days", "Loss"]
    ax.set_xticks(range(4), labels, rotation=25, ha="right"); ax.set_yticks(range(4), labels)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center", color="white" if abs(corr.iloc[i,j]) > .6 else "#263746")
    ax.set_title("Descriptive model correlations")
    fig.colorbar(image, ax=ax, fraction=.045, pad=.03)
    ax = axes[1, 1]
    means = model.groupby("country")[["days_past", "days_recent"]].mean().reindex(countries)
    x = np.arange(4)
    ax.bar(x-.17, means.days_past, .34, color="#9DAEB5", label="Older winters")
    ax.bar(x+.17, means.days_recent, .34, color=[COUNTRY_COLORS[c] for c in countries], label="Recent winters")
    ax.set_xticks(x, countries); ax.set_ylim(0, 145)
    ax.set(title="Modelled period means", ylabel="Days/winter with daily maximum ≥30 cm")
    ax.legend(frameon=False, fontsize=9)
    fig.suptitle("Four-country demonstration — unvalidated model estimates", x=.06, ha="left", fontsize=16, fontweight="bold")
    save(fig, root, "checkpoint_country_model_eda.png", f"{len(model)} distinct returned model reference points · ERA5-Land via Open-Meteo · convenience sample, not a country survey\nModel errors remain substantial; these plots do not validate real snow trends or resort risk. Source-listed elevation is not corrected snow depth.")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    ax = axes[0]
    ax.scatter(measured.observed_lost_days, measured.model_lost_days, color="#16667F", s=38)
    minimum = min(measured.observed_lost_days.min(), measured.model_lost_days.min()) - 5
    maximum = max(measured.observed_lost_days.max(), measured.model_lost_days.max()) + 5
    ax.plot([minimum, maximum], [minimum, maximum], ls="--", color="#84929C")
    ax.axhline(0, color="#CAD2D6", lw=.7); ax.axvline(0, color="#CAD2D6", lw=.7)
    ax.set(xlim=(minimum, maximum), ylim=(minimum, maximum), xlabel="Measured period loss (days/winter)", ylabel="Modelled period loss (days/winter)", title="Does the model reproduce measured changes?")
    row = results["tests"].query('comparison == "station_period_loss" and method == "Pearson"').iloc[0]
    ax.text(.04, .94, f"Pearson r = {row.statistic:.2f}\nNominal p = {row.p_value_nominal:.3f}; n = {len(measured)} stations", transform=ax.transAxes, va="top", fontsize=10)
    ax = axes[1]
    errors = measured.model_lost_days - measured.observed_lost_days
    ax.hist(errors, bins=7, color="#CB6638", edgecolor="white")
    ax.axvline(0, color="#84929C", ls="--"); ax.axvline(errors.mean(), color="#263746", lw=1.5)
    ax.set(title=f"Mean error in period loss: {errors.mean():+.1f} days", xlabel="Model loss − measured loss (days/winter)", ylabel="Number of stations")
    fig.suptitle("SQ2: agreement in change, using one value per station", x=.06, ha="left", fontsize=16, fontweight="bold")
    save(fig, root, "checkpoint_station_change_tests.png", "20 selected Swiss stations; means of ten winters per period · model and measurements both at 06:00 UTC\nP-values are exploratory and assume independence between stations. Correlation does not establish agreement.")

    fits = [("Measured Swiss elevation", results["measured_fit"]),
            ("Model: country + elevation", results["model_fits"]["sq1_model_country_elevation"]),
            ("Model: country × elevation", results["model_fits"]["sq1_model_country_elevation_interaction"])]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for i, (label, fitted) in enumerate(fits):
        ax = axes[0, i]
        ax.scatter(fitted.fittedvalues, fitted.resid, s=28, color="#16667F" if i == 0 else "#CB6638")
        ax.axhline(0, color="#84929C", ls="--")
        ax.set(title=label, xlabel="Fitted loss (days/winter)", ylabel="Residual (days/winter)")
        stats.probplot(np.asarray(fitted.resid), dist="norm", plot=axes[1, i])
        axes[1, i].set(title="Normal Q–Q diagnostic", xlabel="Theoretical normal quantile", ylabel="Ordered residual (days/winter)")
    fig.suptitle("Regression diagnostics: inspect assumptions before interpreting tests", x=.06, ha="left", fontsize=16, fontweight="bold")
    save(fig, root, "checkpoint_regression_diagnostics.png", "Ordinary least squares, one period difference per reference site · five-fold errors are reported separately in the metrics table\nCountry model outputs describe the unvalidated model sample; measured results describe the selected Swiss stations only.")
