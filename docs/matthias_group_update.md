# Matthias: what I can show the group now

**My part:** snow charts/map, the elevation-and-country regression, and checking whether the weather model agrees with real snow measurements.

- The Swiss measurements show **15.4 fewer snow days per winter** in the selected 20-station sample. Lower stations lost more; the regression associates +100 m with about 1.6 fewer days of loss.
- The model check is a real finding: it counts about **54 extra snow days** and does not reproduce the measured change well. We should not call its raw counts reliable resort risk.
- The country regression is implemented on **24 source-checked model reference areas**, six per country. It demonstrates the method and its limits; it is not a validated conclusion about all four countries.
- The interactive map combines 275 candidate ski areas, the model reference sample and 181 approximately located closure records. 3 ambiguous closure entries remain listed and unplotted.
- I fixed the pilot-ID crosswalk: 10 entries now join to 9 current source areas. Original database tables are preserved; new results are in clearly labelled checkpoint tables.

**Open:** `notebooks/03.3_matthias_checkpoints.ipynb` → Run All. Tables and figures appear below the cells. The separate [map file](ski_resorts_closures_map.html) opens after downloading it.

**What still needs a team decision:** how to obtain/validate snow estimates suitable for the full resort study. The original scientific country comparison and risk-based price/closure conclusions remain open. [Full report](matthias_checkpoint_report.md).
