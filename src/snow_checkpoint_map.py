"""A standalone Folium map and a static overview of the checkpoint data.

Leaflet/jQuery are bundled locally; the default map needs no map-tile service.
Municipality positions for closures are explicitly approximate.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from urllib.request import urlopen

import folium
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd
from branca.colormap import LinearColormap

from snow_checkpoint_figures import COUNTRY_COLORS
from snow_validation import distance_km, project_root

ASSETS = {
    "leaflet-1.9.4.js": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js",
    "leaflet-1.9.4.css": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css",
    "jquery-3.7.1.min.js": "https://code.jquery.com/jquery-3.7.1.min.js",
    "Leaflet-LICENSE.txt": "https://raw.githubusercontent.com/Leaflet/Leaflet/v1.9.4/LICENSE",
    "jQuery-LICENSE.txt": "https://raw.githubusercontent.com/jquery/jquery/3.7.1/LICENSE.txt",
}


def download_assets(root):
    folder = Path(root) / "docs/assets"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url in ASSETS.items():
        path = folder / name
        if not path.is_file():
            with urlopen(url, timeout=40) as response:
                path.write_bytes(response.read())
        manifest.append({"path": name, "source_url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "licence": "BSD-2-Clause" if "leaflet" in name.lower() else "MIT"})
    (folder / "map_vendor_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def european_boundaries(root):
    data = json.loads((Path(root) / "data/processed/alpine_map_boundaries.geojson").read_text())
    result = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        keep = [p for p in polygons if -15 < np.mean([xy[0] for xy in p[0]]) < 30
                and 30 < np.mean([xy[1] for xy in p[0]]) < 60]
        if keep:
            result.append({"type": "Feature", "properties": feature["properties"],
                           "geometry": {"type": "MultiPolygon", "coordinates": keep}})
    return {"type": "FeatureCollection", "features": result}


def point_feature(lat, lon, properties):
    if not (np.isfinite(lat) and np.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid map coordinates must not be plotted.")
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": properties}


def geo_layer(features, name, color, radius=5, show=True, fields=None, aliases=None):
    layer = folium.GeoJson({"type": "FeatureCollection", "features": features}, name=name, show=show,
                           marker=folium.CircleMarker(radius=radius, fill=True, fill_opacity=.85, weight=1),
                           style_function=lambda feature: {"color": color(feature), "fillColor": color(feature)},
                           tooltip=folium.GeoJsonTooltip(fields=["Name"], labels=False),
                           popup=folium.GeoJsonPopup(fields=fields, aliases=aliases, labels=True, max_width=420))
    return layer


def build_map(root):
    root = Path(root)
    folder = root / "docs/assets"
    for name in ASSETS:
        if not (folder / name).is_file():
            raise FileNotFoundError("Map assets are missing. Run python src/snow_checkpoint_map.py --download-assets once.")
    roster = pd.read_csv(root / "data/processed/resorts_snow_roster.csv")
    resorts = roster.loc[roster.include_in_alpine_candidate_set].copy().set_index("resort_id")
    sample = pd.read_csv(root / "data/processed/checkpoint_resorts_24.csv")
    summary = pd.read_csv(root / "data/processed/model_resort_summary_checkpoint.csv")
    closures = pd.read_csv(root / "data/processed/legambiente_closure_locations.csv")
    observed = pd.read_csv(root / "data/processed/snow_station_changes.csv")
    for row in sample.itertuples(index=False):
        resorts.loc[row.resort_id, ["latitude", "longitude", "coordinate_method"]] = [row.lat, row.lon, "source_first_listed_lift_access"]
        resorts.loc[row.resort_id, ["source_url", "retrieved_utc", "response_sha256", "access_point_name"]] = [
            row.coordinate_source_url, row.source_retrieved_utc, row.coordinate_source_sha256, row.access_point_name]
        resorts.loc[row.resort_id, ["scope_decision", "scope_reason"]] = ["in_alps", "Named Alpine study area; source-listed access point reviewed before model outcomes"]
    resorts["coordinate_change_km"] = distance_km(resorts.original_latitude, resorts.original_longitude,
                                                resorts.latitude, resorts.longitude)
    resorts = resorts.reset_index()
    resorts.to_csv(root / "data/processed/checkpoint_map_resort_locations.csv", index=False)
    located = closures.loc[closures.geocode_status.eq("matched_municipality_approximate")].copy()
    unresolved = closures.loc[~closures.index.isin(located.index)].copy()
    unresolved.to_csv(root / "data/processed/closure_locations_unresolved.csv", index=False)
    boundaries = european_boundaries(root)
    m = folium.Map(location=[45.5, 10.2], zoom_start=6, tiles=None, prefer_canvas=True,
                   control_scale=True, width="100%", height="100%")
    m.default_js = []; m.default_css = []
    licences = "\n".join((folder / name).read_text() for name in ["Leaflet-LICENSE.txt", "jQuery-LICENSE.txt"])
    m.get_root().header.add_child(folium.Element("<!-- Bundled third-party licences\n" + licences + "\n-->"), name="bundled_licences")
    style = (folder / "leaflet-1.9.4.css").read_text()
    m.get_root().header.add_child(folium.Element("<style>" + style + "</style>"), name="leaflet_css")
    for name in ["leaflet-1.9.4.js", "jquery-3.7.1.min.js"]:
        script = (folder / name).read_text().replace("</script", "<\\/script")
        m.get_root().header.add_child(folium.Element("<script>" + script + "</script>"), name=name)
    folium.GeoJson(boundaries, name="Country outlines", control=False,
                   style_function=lambda f: {"color": "#8798A2", "weight": .8, "fillColor": "#EDF1F0", "fillOpacity": .75}).add_to(m)
    points = []
    for row in resorts.itertuples(index=False):
        points.append(point_feature(row.latitude, row.longitude, {
            "Name": html.escape(row.resort_name), "Country": row.country_for_analysis,
            "Base elevation": f"{row.elevation_base_m} m (source-listed)",
            "Coordinates": row.coordinate_method,
            "Snow data": "Not a validated resort snow-risk measurement"}))
    geo_layer(points, f"{len(resorts)} Alpine candidate areas (source locations)", lambda f: "#768A96", radius=4,
              fields=["Name", "Country", "Base elevation", "Coordinates", "Snow data"]).add_to(m)
    limit = max(1., float(summary.lost_snow_days.abs().max()))
    colors = LinearColormap(["#2166AC", "#F7F7F7", "#B2182B"], vmin=-limit, vmax=limit)
    points = []
    for row in summary.itertuples(index=False):
        points.append(point_feature(row.lat, row.lon, {"Name": html.escape(row.name), "Country": row.country,
            "Past mean": f"{row.days_past:.1f} modelled days/winter", "Recent mean": f"{row.days_recent:.1f} modelled days/winter",
            "Loss": round(row.lost_snow_days, 2), "Evidence": "Unvalidated ERA5-Land demonstration; daily maximum ≥30 cm",
            "Altitude basis": "Source-listed base target; grid snow is not altitude-corrected"}))
    geo_layer(points, f"{len(summary)}-area model demonstration: loss in days", lambda f: colors(f["properties"]["Loss"]), radius=8,
              fields=["Name", "Country", "Past mean", "Recent mean", "Loss", "Evidence", "Altitude basis"]).add_to(m)
    points = [point_feature(row.lat, row.lon, {"Name": html.escape(row.station_name),
               "Elevation": f"{row.elev_m} m", "Loss": round(row.observed_lost_days, 2),
               "Evidence": "MeteoSwiss measured snow depth at 06:00 UTC; selected Swiss stations only"})
              for row in observed.itertuples(index=False)]
    geo_layer(points, "20 Swiss measured stations (teal; loss shown in popup)", lambda f: "#16667F",
              radius=7, show=False, fields=["Name", "Elevation", "Loss", "Evidence"]).add_to(m)
    for status, label, color in [("dismesso", "Abandoned Italian facilities — municipality positions", "#762A83"),
                                 ("chiuso temporaneamente", "Temporarily closed — municipality positions", "#9A651B")]:
        group = located.loc[located.status.eq(status)]
        points = []
        for (town, region), rows in group.groupby(["comune", "region"]):
            first = rows.iloc[0]
            names = "<br>".join(html.escape(str(v)) for v in rows.facility_name)
            points.append(point_feature(first.latitude, first.longitude, {
                "Name": html.escape(str(town)), "Region": html.escape(str(region)), "Extracted facilities": len(rows),
                "Facility names": names, "Location precision": "Municipality/locality only, NOT the individual lift",
                "Source": "Legambiente Nevediversa 2026 extracted sample + OpenStreetMap / Nominatim"}))
        if points:
            geo_layer(points, label, lambda f, shade=color: shade, radius=5,
                      fields=["Name", "Region", "Extracted facilities", "Facility names", "Location precision", "Source"]).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    # A static HTML legend keeps the map fully standalone: Branca's rendered
    # colour bar would otherwise insert a remote D3 script.
    legend = f'''<div style="position:fixed;bottom:36px;right:14px;z-index:9999;background:white;padding:10px 13px;
        width:255px;font:11px/1.4 Arial,sans-serif;border:1px solid #ccd5da;border-radius:6px">
        <strong>MODEL SAMPLE ONLY</strong><br>Past mean − recent mean, snow days/winter
        <div style="height:11px;margin:5px 0;background:linear-gradient(to right,#2166AC,#F7F7F7,#B2182B)"></div>
        <div style="display:flex;justify-content:space-between"><span>{-limit:.1f}</span><span>0</span><span>{limit:.1f}</span></div>
        Blue = more recent days · Red = fewer.<br>Other layers use separate symbols.</div>'''
    m.get_root().html.add_child(folium.Element(legend))
    checked = resorts.coordinate_method.eq("source_first_listed_lift_access").sum()
    panel = f'''<div style="position:fixed;bottom:36px;left:14px;z-index:9999;background:white;padding:13px 16px;
        max-width:365px;font:13px/1.45 Arial,sans-serif;border:1px solid #ccd5da;border-radius:7px;box-shadow:0 2px 9px #0002">
        <strong style="font-size:17px">SCI · Snow and ski-area locations</strong><br>
        Winters ending 1986–1995 versus 2016–2025.<br>
        <strong>Model layer: exploratory, not validated resort risk.</strong><br>
        {len(resorts)} candidate areas; {int(checked)} checked access points; {len(resorts)-int(checked)} other geocodes need review.<br>
        Closures: {len(located)}/{len(closures)} extracted records located approximately; {len(unresolved)} unresolved and not plotted.<br>
        This is the 184-record extracted sample, not a complete census of Italian closures.<br>
        <span style="color:#762A83">●</span> Abandoned &nbsp; <span style="color:#9A651B">●</span> Temporarily closed<br>
        Click a point and use the layer controls. No live data downloads are needed.<br>
        <small>Weather: ECMWF/Copernicus via Open-Meteo. Measurements: MeteoSwiss.<br>
        Closure geocodes: © OpenStreetMap contributors, ODbL; country outlines: Natural Earth, public domain.<br>
        Leaflet: BSD-2-Clause; Folium / jQuery: MIT.</small></div>'''
    m.get_root().html.add_child(folium.Element(panel))
    target = root / "docs/ski_resorts_closures_map.html"
    m.save(target)
    count_table = pd.DataFrame([{"layer": "candidate_resorts", "source_records": len(resorts), "plotted_records": len(resorts)},
                               {"layer": "model_reference_sample", "source_records": len(summary), "plotted_records": len(summary)},
                               {"layer": "measured_swiss_stations", "source_records": len(observed), "plotted_records": len(observed)},
                               {"layer": "extracted_closure_records", "source_records": len(closures), "plotted_records": len(located)},
                               {"layer": "unresolved_closures", "source_records": len(unresolved), "plotted_records": 0}])
    count_table.to_csv(root / "data/processed/checkpoint_map_coverage.csv", index=False)
    static_map(root, boundaries, resorts, summary, located, colors)
    return {"map_path": target, "resorts": resorts, "closure_locations": closures, "coverage": count_table}


def static_map(root, geometry, resorts, sample, closures, colors):
    fig, ax = plt.subplots(figsize=(12, 7.5))
    for feature in geometry["features"]:
        for polygon in feature["geometry"]["coordinates"]:
            ax.add_patch(Polygon(polygon[0], facecolor="#EDF1F0", edgecolor="#A4B2BA", lw=.6))
    ax.scatter(resorts.longitude, resorts.latitude, color="#A7B5BD", s=9, alpha=.6, label="Alpine candidate areas")
    plotted = closures.loc[closures.latitude.between(43, 49.2) & closures.longitude.between(4, 17.5)]
    ax.scatter(plotted.longitude, plotted.latitude, marker="x", s=22, c="#762A83", label=f"Closure records in this view (n={len(plotted)})")
    ax.scatter(sample.lon, sample.lat, c=[colors.rgb_hex_str(v) for v in sample.lost_snow_days], s=55,
               edgecolors="#263746", linewidths=.7, label="24 source-checked model reference areas", zorder=4)
    for country, x, y in [("FR", 5.2, 46.8), ("CH", 8.0, 47.2), ("AT", 13.6, 47.8), ("IT", 11.1, 44.5)]:
        ax.text(x, y, country, fontsize=13, color="#5B6B76", fontweight="bold")
    ax.set(xlim=(4, 17.5), ylim=(43, 49.2), xlabel="Longitude (° E)", ylabel="Latitude (° N)")
    ax.set_aspect(1/np.cos(np.radians(46)))
    ax.set_title("Study locations and extracted closure records", loc="left", fontsize=16, fontweight="bold", pad=16)
    ax.legend(loc="upper left", framealpha=.95, fontsize=9)
    fig.text(.08, .055, "Coloured reference points show unvalidated model loss; red = fewer recent snow days. Gray geocodes include unreviewed locations.", fontsize=9)
    fig.text(.08, .03, "Closures are approximate municipality positions. The interactive map includes all located Italian entries and exact source notes.", fontsize=9)
    fig.text(.08, .008, "Sources: Skiresort / Open-Meteo / Legambiente / OpenStreetMap / Natural Earth · Full methods: docs/matthias_checkpoint_report.md", fontsize=8)
    fig.tight_layout(rect=(.03, .08, .98, .98))
    fig.savefig(Path(root) / "docs/figures/checkpoint_locations_map.png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-assets", action="store_true")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    if args.download_assets:
        download_assets(root)
    else:
        print(build_map(root)["map_path"])
