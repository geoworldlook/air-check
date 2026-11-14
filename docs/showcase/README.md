# Published result

Files in this folder are written by the daily run (`python -m aircheck run`) and served by GitHub Pages.

| File | Content |
|---|---|
| `aircheck_panel.html` | the public panel (one file, data embedded; also opens from disk) |
| `aircheck_data.json` | the same data for notebooks |
| `map_points.geojson` | one point per city for the monitoring map on geoworldlook.vercel.app |
| `status.json` | last run, data quality gate, progress of the live confirmation test |

Live panel: https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html

Do not edit these files by hand: the next run overwrites them.
