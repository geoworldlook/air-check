# Changelog

Versions follow semantic versioning (major.minor.patch).

## 1.1.0 — 2026-11-16

- **Corrected forecast (protocol A2):** a station-level regression (model output statistics): measurement =
  a + b · forecast + c · last known measurement, fitted on the previous 365 days, causal. Chosen among 12 variants
  of five literature methods on data up to 2025-11-15 (`notebooks/experiments/A2_wybor_korekty.py`), then fixed.
- **Hold-out year 2025-11-16 to 2026-11-15, computed once:** the corrected forecast beats persistence in 27 of 27
  cities and beats the raw forecast in 27 of 27 (raw forecast: 13 of 27). Results: `docs/evidence/A2_wyniki.md`.
- **Live:** the corrected day-ahead forecast is saved on the issue day next to the raw one (`pm25_corr`);
  live test window 2026-11-18 to 2027-02-15.
- **Panel:** raw and corrected forecast side by side; corrected forecast for tomorrow; hold-out table.
- **Registry cleanup:** `stations.csv` now holds only active stations (27). New rule: at least 75% of days in the
  last 90 days; Bergen removed for missing current data. Deviations from protocol A1: `docs/evidence/A1_odstepstwa.md`.
- **Robust schedule:** three scheduled attempts a day, patient retry on provider rate limits, the live forecast
  is saved before the archive refresh, the failure issue is closed automatically after a successful run.

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
