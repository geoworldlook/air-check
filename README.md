# Air Check: is the air-quality forecast right in my city?

[![selftest](https://github.com/geoworldlook/air-check/actions/workflows/selftest.yml/badge.svg)](https://github.com/geoworldlook/air-check/actions/workflows/selftest.yml)
[![daily](https://github.com/geoworldlook/air-check/actions/workflows/daily.yml/badge.svg)](https://github.com/geoworldlook/air-check/actions/workflows/daily.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-1.1.0-green)

Air Check tests the daily fine-dust (PM2.5) forecast of the
[Copernicus Atmosphere Monitoring Service](https://atmosphere.copernicus.eu/) (CAMS) against official ground stations
in 27 European cities, and then makes it better. Every day it saves the new forecast, compares the old forecast with
what the stations measured, applies a small statistical correction, and publishes the result. The yardstick is the
simplest forecast there is: "tomorrow will be like today" (called *persistence*). A forecast is useful in a city only
if it beats this rule.

**[Live panel](https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html)** (updated automatically every day)

**Checked against the ground (hold-out year 2025-11-16 to 2026-11-15):**

- The **raw** Copernicus forecast beats "tomorrow = today" in 13 of 27 cities. In Katowice, Milano, Warszawa and
  Torino it is much worse than the rule, mostly because it is too high in winter.
- The **corrected** forecast beats the rule in **27 of 27 cities** and beats the raw forecast in 27 of 27. The median
  error falls from 5.5 to 4.0 µg/m³ (the rule: 5.2). In Katowice the error falls from 18.8 to 4.8 µg/m³.
- The correction method was chosen on earlier data and fixed in a protocol before the hold-out year was computed.
  Two live tests with rules fixed in advance are running until February 2027.

## Product card

| | |
|---|---|
| **Problem** | CAMS forecasts air quality for all of Europe, but a person cannot see how good the forecast is in their own city. In cities with heavy winter smog the raw forecast is often worse than assuming that tomorrow will be like today. |
| **User** | Residents, journalists and city staff who read smog forecasts; people who use CAMS data in apps and reports. |
| **Solution** | A small pipeline that runs every day without a person: station measurements (EEA) + today's CAMS forecast → data quality gate → station-level correction → scores → public panel and map points. The state is a few small CSV tables in this repository, so the run needs only GitHub Actions. |
| **Evidence** | 27 cities in 6 countries, daily mean PM2.5, about 300–365 compared days per city in the hold-out year. Corrected forecast better than persistence in 27 of 27 cities and better than the raw forecast in 27 of 27 (both rules of protocol A2 confirmed); raw forecast better than persistence in 13 of 27. |
| **Status** | Runs every day without manual work. Live confirmation tests for the raw forecast (protocol A1) and the corrected forecast (protocol A2) are in progress. Self-assessed technology readiness: TRL 4–5 (working end to end on real data; not yet tested with users). |
| **Limits** | One station per city and one pollutant (PM2.5). A station is a point; the forecast is a square of about 10 km. The archive holds forecasts with a lead time below one day, so a true day-ahead forecast is harder; only the live tests measure it. The correction needs fresh station data. No statement about health effects or legal limits. |
| **Next** | Verdicts of the live tests in February 2027; forecasts read directly from the Copernicus Atmosphere Data Store; more pollutants (PM10, NO2); national real-time feeds for cities missing from the EEA feed. |

## Results

Hold-out year 2025-11-16 to 2026-11-15. RMSE is the typical error in µg/m³. Skill is
1 − MSE(forecast) / MSE(persistence): above 0 the forecast is better than the rule.

| | Raw Copernicus forecast | Corrected forecast | "Tomorrow = today" |
|---|---|---|---|
| Cities where it beats the rule | 13 of 27 | **27 of 27** | — |
| Median error (RMSE) | 5.5 | **4.0** | 5.2 |
| Median skill | −0.03 | **0.46** | 0 |

Examples (error in µg/m³: raw → corrected, rule in brackets):

| City | Raw | Corrected | Rule |
|---|---|---|---|
| Katowice | 18.8 | 4.8 | 6.5 |
| Milano | 17.4 | 6.7 | 9.5 |
| Warszawa | 10.2 | 5.6 | 7.7 |
| Torino | 9.0 | 5.7 | 6.8 |
| Gdańsk | 6.4 | 5.3 | 7.9 |
| Paris | 3.8 | 3.2 | 5.0 |
| Helsinki | 2.6 | 2.2 | 3.9 |

All numbers for every city are in the
[panel](https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html) and in
[`docs/showcase/aircheck_data.json`](docs/showcase/aircheck_data.json).
Details: [A2 results](docs/evidence/A2_wyniki.md) (in Polish).

### Negative and inconclusive results

- **The raw forecast loses to the simplest rule in 14 of 27 cities** in the hold-out year, mostly where winter fine
  dust is high (southern Poland, the Po Valley) and in Alpine valleys. Winter over-forecast: Milano +19 µg/m³,
  Katowice +12, Warszawa +9, Torino +7. The cause was not investigated.
- **The weakest gains** of the corrected forecast are in Grenoble and Annecy (skill 0.21 and 0.25).
- **High-dust days** (above 25 µg/m³) are caught better by the corrected forecast in the cities with many such
  days, but not everywhere: in a few cities with few such days (Basel, Annecy, Bordeaux) the hit score stays below
  the rule's.
- **Other correction methods did worse** on the development data: a running bias correction and a Kalman filter beat
  the rule in only 18–22 of 27 cities. The comparison is in
  [`docs/evidence/A2_wybor_korekty.csv`](docs/evidence/A2_wybor_korekty.csv).
- **Forecast skill before November 2023 cannot be checked:** the forecast archive starts there. The CAMS reanalysis
  for earlier years is not used as evidence, because it takes in measurements from the same stations.
- **20 of 47 candidate cities are not in the registry:** no urban background station with PM2.5 in both EEA feeds,
  too many missing days, or no current data (Bergen was removed for that reason on 2026-11-16). The list with
  reasons is in [`docs/evidence/A0_przeglad_stacji.md`](docs/evidence/A0_przeglad_stacji.md).

## Method

1. **Stations.** One urban or suburban background station per city, chosen by a written rule: within 15 km
   (20 km for large cities), PM2.5 in both EEA feeds, at least 75% of days in every year since 2022 and in the last
   90 days ([`aircheck/registry.py`](aircheck/registry.py)).
2. **Measurement.** Daily mean in UTC from at least 18 valid hours, or the daily value reported by the network.
   Days with a stuck sensor (at most two different values) are dropped.
3. **Forecast.** CAMS ensemble, daily mean in UTC at the station location. The forecast issued today is saved with
   its issue date and never changed. Archived forecasts (lead below one day) are used for the reconstruction.
4. **Correction.** A regression per station, `measurement = a + b · forecast + c · last known measurement`, fitted on
   the previous 365 days. It uses only data from before the forecast day. This family of methods (model output
   statistics, MOS) is standard for air-quality forecasts: see Bertrand et al. 2023 (Atmos. Chem. Phys. 23, 5317),
   Riccio and Chianese 2024 (Atmos. Chem. Phys. 24, 1673) and Delle Monache et al. 2006 for the Kalman-filter variant
   ([`aircheck/correct.py`](aircheck/correct.py)).
5. **Scores.** RMSE of the forecast and of persistence, skill score with a 95% interval (block bootstrap, 7-day
   blocks), and hits, misses and false alarms for days above 25 µg/m³.
6. **Data quality gate.** If fewer than half of the stations have a fresh measurement, or today's forecast is
   missing, the panel is not updated and the run fails with an issue.
7. **Protocols.** [A1](docs/evidence/A1_protokol_prognozy.md) (raw forecast) and
   [A2](docs/evidence/A2_protokol_korekta.md) (corrected forecast) fix the windows, the scores and the decision rules
   in advance (in Polish). Their SHA-256 sums are stored in the code and checked in CI.

## Code

| Path | Content |
|---|---|
| [`aircheck/`](aircheck/) | package: `sources/` (EEA, CAMS), `correct.py` (correction), `core.py` (scores), `pipeline.py`, `publish.py`, `registry.py`, `selftest.py` |
| [`aircheck/stations.csv`](aircheck/stations.csv) | station registry with data completeness per year |
| [`data/`](data/) | pipeline state: daily measurements and forecasts as small CSV tables |
| [`docs/showcase/`](docs/showcase/) | published result: panel, data, map points, run status |
| [`docs/`](docs/) | documentation in Polish: status and plan, architecture, how to run, step-by-step guide, protocols and results |
| [`notebooks/`](notebooks/) | blog notebook generator; `experiments/` with the method-selection experiment |
| [`.github/workflows/`](.github/workflows/) | `daily.yml` (the run), `selftest.yml` (linter, offline test, container build) |

## How to run

```bash
pip install -e .
```

```bash
python -m aircheck selftest
```

```bash
python -m aircheck run
```

`selftest` needs no network (about a minute). `run` does what the scheduled job does. Other commands: `backfill`
(rebuild the history since 2022), `render` (rebuild the panel from stored tables), `publish`, `settings`, `stations`.
With Docker: `docker build -t air-check .` and `docker run --rm -v "$PWD:/work" -e AIRCHECK_ROOT=/work air-check run`.
A conda environment file is included (`environment.yml`).

## Data and attribution

- **Measurements:** European Environment Agency (EEA), Air Quality e-Reporting, verified (E1a) and up-to-date (UTD)
  data reported by the national networks, through the EEA Air Quality Download Service. EEA content is published
  under CC BY 4.0 unless stated otherwise. The daily means here are computed by Air Check (modified data).
- **Forecast:** generated using Copernicus Atmosphere Monitoring Service information: CAMS European air quality
  forecasts (ensemble), CC-BY licence. Neither the European Commission nor ECMWF is responsible for any use of
  this information.
- **Access to the forecast:** [Open-Meteo](https://open-meteo.com/) Air Quality API, free for non-commercial use,
  attribution required.
- **Map in the panel:** © OpenStreetMap contributors; Leaflet 1.9.4 (BSD-2-Clause, style sheet embedded).

## How it is built

I build this project with help from Claude, an AI assistant made by Anthropic. Claude helps with code, analysis runs
and documentation. I set the goals and the methods, review the results and make the decisions. Every result is
checked against ground measurements, as described above.

## License

Code: [MIT](LICENSE). Data remain under their providers' licences (above). Documentation in [`docs/`](docs/) is in
Polish.
