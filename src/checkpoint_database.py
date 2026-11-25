"""Resolve historical pilot IDs and add qualified checkpoint tables to SQLite.

Existing team tables are preserved. Model demonstration tables are named and
labelled explicitly, without promoting them to validated resort risk classes.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

ALIASES = {
    "zermatt-matterhorn": "zermatt-breuil-cervinia-valtournenche-matterhorn",
    "breuil-cervinia-valtournenche-zermatt": "zermatt-breuil-cervinia-valtournenche-matterhorn",
    "st-moritz-corviglia": "st-moritz-corviglia",
    "andermatt-sedrun-disentis": "andermatt-oberalp-sedrun",
    "livigno": "livigno", "aprica": "aprica",
    "kitzbuehel-kirchberg": "kitzski-kitzbuehel-kirchberg", "soelden": "soelden",
    "les-houches-saint-gervais-chamonix": "les-houches-saint-gervais-prarion-bellevue-chamonix",
    "les-2-alpes": "les-2-alpes",
}


def build_crosswalk(root):
    root = Path(root)
    pilot = pd.read_csv(root / "data/processed/pilot_resort_locations.csv")
    roster = pd.read_csv(root / "data/processed/resorts_snow_roster.csv")
    if set(pilot.resort_id) != set(ALIASES):
        raise ValueError("The historical pilot changed; inspect its ID mapping before proceeding.")
    rows = []
    for row in pilot.itertuples(index=False):
        canonical = ALIASES[row.resort_id]
        match = roster.loc[roster.resort_id.eq(canonical)]
        if len(match) != 1:
            raise ValueError(f"Canonical area ID is missing or duplicated: {canonical}")
        target = match.iloc[0]
        note = "historical source slug/name to current canonical source URL"
        if row.resort_id == "andermatt-sedrun-disentis":
            note += "; pilot reference is the Andermatt gateway, not an independently verified Disentis measurement"
        rows.append({"pilot_resort_id": row.resort_id, "pilot_name": row.name, "pilot_country": row.country,
                     "canonical_resort_id": canonical, "canonical_name": target.resort_name,
                     "country_memberships": target.country_memberships,
                     "source_url": target.url, "mapping_basis": note,
                     "gateway_of_cross_border_area": target.country_for_analysis == "cross_border"})
    result = pd.DataFrame(rows)
    if result.pilot_resort_id.duplicated().any() or len(result) != len(pilot):
        raise ValueError("Every historical pilot entry needs exactly one mapping.")
    result.to_csv(root / "data/processed/pilot_resort_id_crosswalk.csv", index=False)
    return result


def quoted(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def table_snapshot(connection, names):
    result = {}
    for name in names:
        columns = connection.execute(f"PRAGMA table_info({quoted(name)})").fetchall()
        rows = connection.execute(f"SELECT * FROM {quoted(name)} ORDER BY rowid").fetchall()
        body = json.dumps({"columns": columns, "rows": rows}, ensure_ascii=False, default=str).encode()
        result[name] = (len(rows), hashlib.sha256(body).hexdigest())
    return result


def update_checkpoint_database(root, crosswalk):
    root = Path(root)
    source = root / "db/sci_alpi.db"
    if not source.is_file():
        raise FileNotFoundError("Luca's SQLite database must exist before checkpoint integration.")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'checkpoint_%' AND name != 'pilot_resort_id_crosswalk'")]
        original = table_snapshot(conn, names)
        handle = tempfile.NamedTemporaryFile(prefix=".checkpoint-", suffix=".sqlite", dir=source.parent, delete=False)
        temporary = Path(handle.name); handle.close()
        with sqlite3.connect(temporary) as target:
            conn.backup(target)
    data = root / "data/processed"
    mapping = {
        "checkpoint_snow_model_winters": "model_resort_winters_checkpoint.csv",
        "checkpoint_snow_model_summary": "model_resort_summary_checkpoint.csv",
        "checkpoint_closure_locations": "legambiente_closure_locations.csv",
        "checkpoint_climate_model_metrics": "snow_checkpoint_regression_metrics.csv",
        "checkpoint_climate_coefficients": "snow_checkpoint_regression_coefficients.csv",
        "checkpoint_station_tests": "snow_checkpoint_station_tests.csv",
    }
    try:
        with sqlite3.connect(temporary) as conn:
            crosswalk.to_sql("pilot_resort_id_crosswalk", conn, if_exists="replace", index=False)
            for table, file in mapping.items():
                pd.read_csv(data / file).to_sql(table, conn, if_exists="replace", index=False)
            pd.DataFrame([
                {"dataset": "checkpoint_snow_model_summary", "status": "unvalidated model demonstration; not resort risk", "validated_for_risk_classes": 0},
                {"dataset": "station_winters", "status": "selected measured Swiss stations; site histories and extrapolation limits apply", "validated_for_risk_classes": 0},
                {"dataset": "checkpoint_closure_locations", "status": "approximate municipality/locality positions, not lift GPS", "validated_for_risk_classes": 0}
            ]).to_sql("checkpoint_data_quality", conn, if_exists="replace", index=False)
            lost = conn.execute("""SELECT COUNT(*) FROM pilot_resort_id_crosswalk AS c
                LEFT JOIN resort_roster AS r ON c.canonical_resort_id=r.resort_id
                WHERE r.resort_id IS NULL""").fetchone()[0]
            if lost:
                raise ValueError("Historical pilot mappings were lost in the canonical-area join.")
            snow_count = conn.execute("SELECT COUNT(*) FROM checkpoint_snow_model_summary").fetchone()[0]
            joined = conn.execute("""SELECT COUNT(*) FROM checkpoint_snow_model_summary AS s
                JOIN resort_roster AS r ON s.resort_id=r.resort_id""").fetchone()[0]
            if snow_count != joined:
                raise ValueError("The model summary must join one-to-one to the canonical roster.")
            if table_snapshot(conn, names) != original:
                raise ValueError("An original team table changed during checkpoint integration.")
            result = pd.read_sql_query("""SELECT country, COUNT(*) AS n_reference_areas,
                AVG(days_past) AS mean_model_days_past, AVG(days_recent) AS mean_model_days_recent,
                AVG(lost_snow_days) AS mean_model_loss
                FROM checkpoint_snow_model_summary GROUP BY country ORDER BY country""", conn)
            result["evidence_status"] = "unvalidated ERA5-Land model demonstration"
            result.to_csv(data / "checkpoint_sql_country_summary.csv", index=False)
            conn.commit()
        if hashlib.sha256(source.read_bytes()).hexdigest() != source_digest:
            raise RuntimeError("The original SQLite file changed concurrently; refusing to replace it.")
        temporary.replace(source)
    finally:
        if temporary.exists():
            temporary.unlink()
    audit = pd.DataFrame([
        {"join": "pilot entries to canonical area IDs", "input_rows": len(crosswalk), "output_rows": len(crosswalk), "lost_rows": 0,
         "distinct_canonical_areas": crosswalk.canonical_resort_id.nunique(), "note": "Zermatt and Cervinia remain two gateways of one connected area"},
        {"join": "model reference areas to canonical roster", "input_rows": snow_count, "output_rows": joined, "lost_rows": 0,
         "distinct_canonical_areas": snow_count, "note": "one summary per source area; unvalidated snow model"}])
    audit.to_csv(data / "checkpoint_join_audit.csv", index=False)
    return audit
