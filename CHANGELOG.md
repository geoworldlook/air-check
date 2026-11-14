# Changelog

Versions follow semantic versioning (major.minor.patch).

## 1.0.0 — 2026-11-14

First version, built in the GeoWorldLook project standard (decision D-096).

- **Package `aircheck`:** `python -m aircheck run | backfill | render | publish | selftest | settings | stations`.
- **Sources:** station measurements from the EEA Air Quality Download Service (verified and up-to-date data);
  CAMS European air quality forecast through the Open-Meteo Air Quality API.
- **Station registry:** 28 cities in 7 countries chosen by a written rule (urban background station, PM2.5 in both
  EEA feeds, at least 75% of days in every year since 2022); 19 candidate cities excluded with reasons.
- **Reconstruction:** measurements since 2022-01-01, archived forecasts since 2023-11-01.
- **Scores:** RMSE, skill against persistence with a block-bootstrap interval, critical success index for days
  above 25 µg/m³; verdict per city.
- **Data quality gate** before publication; failed daily runs open an issue.
- **Published result:** panel (one HTML file), data JSON, map points (GeoJSON), run status in `docs/showcase/`.
- **Automation:** daily run in GitHub Actions; CI with linter, offline end-to-end test and container build.
- **Protocol A1** for the live confirmation test (2026-11-16 to 2027-02-13), registered before the first test day.
