# Integration log

| Date | Source | Joined to | Key | Before | After | Lost | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Lorenzo's `pilot_resorts_10.csv` | `pilot_resort_locations.csv` | resort name and country | 10 | 10 | 0 | IDs derived from Lorenzo's source URLs. Added documented base-town coordinates. |
| 2026-11-11 | Open-Meteo hourly responses | Resort input | resort ID and winter | 10 pilot resorts | 20 base/top comparisons | 0 | Two test winters per resort. Count complete UTC days with daily maximum snow depth ≥ 0.30 m. |
| 2026-11-11 | Open-Meteo study winters | Resort input | resort ID and winter | 10 pilot resorts | 200 complete resort winters | 0 | Ten winters per period, at the supplied base elevation. Final counts are recorded after completion. |
| 2026-11-10 | MeteoSwiss manual snow observations | Station metadata and inventory | station ID | 55 candidate stations above 1,000 m | 20 complete stations, 400 station winters | 35 stations | Require complete observations for every study winter. |
