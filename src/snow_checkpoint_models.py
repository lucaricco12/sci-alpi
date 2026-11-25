"""SQ1 climate regressions and SQ2 station-level quality checks.

Observed Swiss results and unvalidated four-country model demonstrations
remain separate. Repeated winters are not treated as independent stations.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.model_selection import KFold, StratifiedKFold

from checkpoint_sample import summarize_panel
from snow_validation import compute_results, load_observations, pair_sources

SEED = 20261125


def design_matrix(frame, elevation, include_country=False, interaction=False):
    height = (frame[elevation].astype(float) - 1500.) / 100.
    result = pd.DataFrame({"Intercept": np.ones(len(frame)), "elevation_per_100m": height}, index=frame.index)
    if include_country:
        if not frame.country.isin(["CH", "IT", "AT", "FR"]).all():
            raise ValueError("Country model requires the four named study countries.")
        for country in ["IT", "AT", "FR"]:
            indicator = frame.country.eq(country).astype(float)
            result[f"country_{country}_vs_CH_at_1500m"] = indicator
            if interaction:
                result[f"elevation_x_{country}"] = height * indicator
    return result


def fit_regression(frame, target, elevation, model_id, unit_column, include_country=False, interaction=False):
    frame = frame.reset_index(drop=True).copy()
    if frame[unit_column].duplicated().any() or frame[[target, elevation]].isna().any().any():
        raise ValueError("Regressions need one complete period difference per independent reference site.")
    if include_country and set(frame.country) != {"CH", "IT", "AT", "FR"}:
        raise ValueError("Country effects cannot be estimated from a Swiss-only sample.")
    x = design_matrix(frame, elevation, include_country, interaction)
    y = frame[target].astype(float)
    if len(frame) <= x.shape[1] or np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError("Insufficient independent data or rank-deficient climate model.")
    fit = sm.OLS(y, x).fit()
    predictions = np.full(len(frame), np.nan)
    baseline = np.full(len(frame), np.nan)
    fold_numbers = np.full(len(frame), -1)
    if include_country:
        if frame.country.value_counts().min() < 5:
            raise ValueError("Five-fold country-stratified validation needs at least five sites per country.")
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(x, frame.country)
    else:
        folds = KFold(n_splits=5, shuffle=True, random_state=SEED).split(x)
    for fold, (train, test) in enumerate(folds, start=1):
        if np.linalg.matrix_rank(x.iloc[train]) != x.shape[1]:
            raise ValueError("A training fold cannot identify the specified model.")
        trained = sm.OLS(y.iloc[train], x.iloc[train]).fit()
        predictions[test] = trained.predict(x.iloc[test])
        baseline[test] = y.iloc[train].mean()
        fold_numbers[test] = fold
    if not np.isfinite(predictions).all():
        raise ValueError("Every site needs a prediction from a model that did not train on that site.")
    interval = fit.conf_int()
    coefficients = pd.DataFrame({"term": x.columns, "estimate": fit.params.to_numpy(),
                                 "std_error": fit.bse.to_numpy(), "t_statistic": fit.tvalues.to_numpy(),
                                 "p_value_nominal": fit.pvalues.to_numpy(),
                                 "ci95_low": interval.iloc[:, 0].to_numpy(), "ci95_high": interval.iloc[:, 1].to_numpy()})
    coefficients.insert(0, "model_id", model_id)
    metrics = {"model_id": model_id, "n_reference_sites": len(frame), "n_parameters": x.shape[1],
               "residual_df": fit.df_resid, "r_squared": fit.rsquared, "adjusted_r_squared": fit.rsquared_adj,
               "rmse_in_sample_days": float(np.sqrt(np.mean(fit.resid**2))),
               "rmse_5fold_days": float(np.sqrt(np.mean((y - predictions)**2))),
               "rmse_5fold_training_mean_days": float(np.sqrt(np.mean((y - baseline)**2))),
               "overall_f_p_value_nominal": fit.f_pvalue, "cv_seed": SEED,
               "outcome": "past-period mean minus recent-period mean; snow days per winter",
               "inference_note": "exploratory nominal p-values; spatial dependence and sample selection remain"}
    values = pd.DataFrame({"model_id": model_id, "reference_id": frame[unit_column],
                           "observed_outcome_days": y, "fitted_days": fit.fittedvalues,
                           "residual_days": fit.resid, "heldout_prediction_days": predictions,
                           "heldout_mean_baseline_days": baseline, "heldout_fold": fold_numbers,
                           "elevation_m": frame[elevation]})
    if "country" in frame:
        values["country"] = frame.country
    return fit, coefficients, metrics, values


def group_eda(frame, fields, group, source_label):
    rows = []
    for label, selected in [("all", frame), *list(frame.groupby(group, observed=True))]:
        for field in fields:
            v = selected[field].dropna().astype(float)
            rows.append({"source": source_label, "group": str(label), "variable": field, "n": len(v),
                         "mean": v.mean(), "median": v.median(), "std": v.std(ddof=1),
                         "min": v.min(), "q25": v.quantile(.25), "q75": v.quantile(.75),
                         "max": v.max(), "skewness": v.skew(), "excess_kurtosis": v.kurt()})
    return pd.DataFrame(rows)


def nominal_anova(frame, outcome, group, source_label):
    groups = [(str(name), values[outcome].astype(float).to_numpy()) for name, values in frame.groupby(group, observed=True)]
    if len(groups) < 2 or any(len(v) < 2 for _, v in groups):
        return {"source": source_label, "test": "one_way_anova", "group": group,
                "n_reference_sites": len(frame), "groups": ";".join(f"{k}:{len(v)}" for k, v in groups),
                "status": "insufficient_group_sizes"}
    f, p = stats.f_oneway(*[v for _, v in groups])
    return {"source": source_label, "test": "one_way_anova", "group": group,
            "n_reference_sites": len(frame), "groups": ";".join(f"{k}:{len(v)}" for k, v in groups),
            "statistic": f, "p_value_nominal": p, "status": "exploratory; assumptions and spatial dependence apply"}


def station_quality(pairs, changes):
    if changes.station_id.duplicated().any():
        raise ValueError("Change tests must use one record per station.")
    records = []
    means = pairs.groupby("station_id")[["observed_days_06utc", "model_days_06utc", "error_days"]].mean()
    for comparison, x, y in [
        ("station_period_loss", changes.observed_lost_days, changes.model_lost_days),
        ("station_mean_snow_days", means.observed_days_06utc, means.model_days_06utc)]:
        for method, function in [("Pearson", stats.pearsonr), ("Spearman", stats.spearmanr)]:
            result = function(x, y)
            records.append({"comparison": comparison, "method": method, "n_station_units": len(x),
                            "statistic": float(result.statistic), "p_value_nominal": float(result.pvalue),
                            "unit": "one station", "inference_note": "nominal; neighbouring stations may be dependent"})
    paired = stats.ttest_rel(changes.model_lost_days, changes.observed_lost_days)
    records.append({"comparison": "model_minus_observed_period_loss", "method": "paired_t_test",
                    "n_station_units": len(changes), "statistic": paired.statistic,
                    "p_value_nominal": paired.pvalue, "unit": "one station",
                    "inference_note": "nominal; tests mean paired error in period loss, not agreement"})
    rng = np.random.default_rng(SEED)
    indices = rng.integers(0, len(changes), size=(5000, len(changes)))
    loss_errors = (changes.model_lost_days - changes.observed_lost_days).to_numpy()
    # Each bootstrap draw resamples whole stations. The 400 repeated winters
    # are never presented as 400 independent climate locations.
    boot_loss = loss_errors[indices].mean(axis=1)
    mean_errors = means.reindex(changes.station_id).error_days.to_numpy()
    boot_bias = mean_errors[indices].mean(axis=1)
    uncertainty = pd.DataFrame([
        {"metric": "mean_model_minus_observed_loss_days", "estimate_days": loss_errors.mean(),
         "ci95_low": np.quantile(boot_loss, .025), "ci95_high": np.quantile(boot_loss, .975)},
        {"metric": "mean_model_minus_observed_snow_days", "estimate_days": mean_errors.mean(),
         "ci95_low": np.quantile(boot_bias, .025), "ci95_high": np.quantile(boot_bias, .975)}])
    uncertainty["resampling_unit"] = "whole station; exploratory, does not correct spatial dependence"
    uncertainty["bootstrap_draws"] = 5000
    uncertainty["seed"] = SEED
    return pd.DataFrame(records), uncertainty


def run_models(root):
    root = Path(root)
    output = root / "data/processed"
    observations = load_observations(root)
    pairs = pair_sources(observations, pd.read_csv(output / "station_model_winters.csv"))
    _, changes, _ = compute_results(pairs)
    changes["country"] = "CH"
    changes["elevation_band"] = pd.cut(changes.elev_m, [-np.inf, 1500, 2000, np.inf],
                                        labels=["below_1500m", "1500_to_below_2000m", "at_least_2000m"], right=False)
    changes["elevation_group_1500m"] = np.where(changes.elev_m.lt(1500), "below_1500m", "at_least_1500m")
    fit, coefs, metrics, predictions = fit_regression(changes, "observed_lost_days", "elev_m",
                                                    "sq1_measured_swiss_elevation", "station_id")
    results = {"measured_fit": fit, "measured_data": changes}
    coefficient_tables, metrics_rows, prediction_tables = [coefs], [metrics], [predictions]
    descriptions = [group_eda(changes, ["observed_days_past", "observed_days_recent", "observed_lost_days"],
                              "elevation_band", "measured_swiss_stations")]
    anovas = [nominal_anova(changes, "observed_lost_days", "elevation_band", "measured_swiss_stations"),
              nominal_anova(changes, "observed_lost_days", "elevation_group_1500m", "measured_swiss_stations")]
    sample = pd.read_csv(output / "checkpoint_resorts_24.csv")
    panel = pd.read_csv(output / "model_resort_winters_checkpoint.csv")
    summary = summarize_panel(sample, panel)
    summary.to_csv(output / "model_resort_summary_checkpoint.csv", index=False)
    # Shared grid cells can give identical outcomes at several resorts. Use a
    # deterministic single reference per returned grid in the model regression.
    model_sites = summary.sort_values("resort_id").drop_duplicates(["grid_lat", "grid_lon"]).copy()
    model_sites["elevation_band"] = pd.cut(model_sites.elev_base_m, [-np.inf, 1500, 2000, np.inf],
                                           labels=["below_1500m", "1500_to_below_2000m", "at_least_2000m"], right=False)
    fitted = {}
    for interaction in [False, True]:
        name = "sq1_model_country_elevation" + ("_interaction" if interaction else "")
        f, c, m, pred = fit_regression(model_sites, "lost_snow_days", "elev_base_m", name, "resort_id",
                                       include_country=True, interaction=interaction)
        coefficient_tables.append(c); metrics_rows.append(m); prediction_tables.append(pred)
        fitted[name] = f
    f_stat, p, df = fitted["sq1_model_country_elevation_interaction"].compare_f_test(fitted["sq1_model_country_elevation"])
    nested = pd.DataFrame([{"comparison": "country-specific elevation slopes versus shared elevation slope",
                            "statistic": f_stat, "p_value_nominal": p, "df_difference": df,
                            "source": "unvalidated four-country model demonstration"}])
    descriptions.append(group_eda(model_sites, ["days_past", "days_recent", "lost_snow_days"], "country", "unvalidated_era5_land_sample"))
    anovas.extend([nominal_anova(model_sites, "lost_snow_days", "country", "unvalidated_era5_land_sample"),
                   nominal_anova(model_sites, "lost_snow_days", "elevation_band", "unvalidated_era5_land_sample")])
    correlation = model_sites[["elev_base_m", "days_past", "days_recent", "lost_snow_days"]].corr()
    correlation.to_csv(output / "snow_checkpoint_model_correlations.csv", index_label="variable")
    pd.crosstab(model_sites.country, model_sites.elevation_band).to_csv(output / "snow_checkpoint_country_elevation_counts.csv")
    pd.concat(descriptions, ignore_index=True).to_csv(output / "snow_checkpoint_descriptive_statistics.csv", index=False)
    pd.concat(coefficient_tables, ignore_index=True).to_csv(output / "snow_checkpoint_regression_coefficients.csv", index=False)
    pd.DataFrame(metrics_rows).to_csv(output / "snow_checkpoint_regression_metrics.csv", index=False)
    pd.concat(prediction_tables, ignore_index=True).to_csv(output / "snow_checkpoint_regression_predictions.csv", index=False)
    pd.DataFrame(anovas).to_csv(output / "snow_checkpoint_anova.csv", index=False)
    nested.to_csv(output / "snow_checkpoint_interaction_test.csv", index=False)
    quality, uncertainty = station_quality(pairs, changes)
    quality.to_csv(output / "snow_checkpoint_station_tests.csv", index=False)
    uncertainty.to_csv(output / "snow_checkpoint_station_uncertainty.csv", index=False)
    results.update(model_data=model_sites, model_fits=fitted, sample_summary=summary,
                   regression_metrics=pd.DataFrame(metrics_rows), coefficients=pd.concat(coefficient_tables),
                   tests=quality, uncertainty=uncertainty)
    return results


if __name__ == "__main__":
    from snow_validation import project_root
    results = run_models(project_root(Path(__file__).resolve().parent))
    print(results["regression_metrics"].to_string(index=False))
