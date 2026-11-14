# Air Check: is the air-quality forecast right in my city?

[![selftest](https://github.com/geoworldlook/air-check/actions/workflows/selftest.yml/badge.svg)](https://github.com/geoworldlook/air-check/actions/workflows/selftest.yml)
[![daily](https://github.com/geoworldlook/air-check/actions/workflows/daily.yml/badge.svg)](https://github.com/geoworldlook/air-check/actions/workflows/daily.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-1.0.0-green)

Air Check tests the daily fine-dust (PM2.5) forecast of the
[Copernicus Atmosphere Monitoring Service](https://atmosphere.copernicus.eu/) (CAMS) against official ground stations
in 28 European cities. Every morning it saves the new forecast, compares yesterday's forecast with what the stations
measured, and publishes the result. The yardstick is the simplest forecast there is: "tomorrow will be like today"
(called *persistence*). A forecast is useful in a city only if it beats this rule.

**[Live panel](https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html)** (updated automatically every day)

**Checked against the ground (last 365 days to 2026-11-13, reconstructed from the forecast archive):** in 9 of 28
cities the forecast is clearly better than "tomorrow = today", in 7 it is clearly worse, and in 12 there is no clear
difference. The forecast wins in Helsinki, Tampere, Oulu, Malmö, Paris, Lyon, Marseille, Toulouse and Gdańsk. The
simple rule wins in Katowice, Warszawa, Milano, Torino, Napoli, Grenoble and Annecy. A live test with rules fixed in
advance runs from 2026-11-16 to 2027-02-13.

## Product card

| | |
|---|---|
| **Problem** | CAMS forecasts air quality for all of Europe, but a person cannot see how good the forecast is in their own city. Official evaluations give results per region and in technical terms. |
| **User** | Residents, journalists and city staff who read smog forecasts; people who use CAMS data in apps and reports. |
| **Solution** | A small pipeline that runs every day without a person: station measurements (EEA) + today's CAMS forecast → data quality gate → scores → public panel and map points. The state is a few small CSV tables in this repository, so the run needs only GitHub Actions. |
| **Evidence** | 28 cities in 7 countries, daily mean PM2.5, about 280–365 compared days per city. Forecast better than persistence in 9 cities, worse in 7, no clear difference in 12 (95% block-bootstrap interval of the skill score). Large winter over-forecast in Milano (+19 µg/m³), Katowice (+12), Warszawa (+9) and Torino (+7). These numbers are descriptive: the rules were written after the data existed. |
| **Status** | Runs every day without manual work. The confirmation test (protocol A1, registered before the first test day) is in progress. Self-assessed technology readiness: TRL 4–5 (working end to end on real data; not yet tested with users). |
| **Limits** | One station per city and one pollutant (PM2.5). A station is a point; the forecast is a square of about 10 km. Current-year measurements are preliminary. The archive holds forecasts with a lead time below one day, so the true day-ahead forecast can be worse; only the live test measures it. No statement about health effects or legal limits. |
| **Next** | Verdict of the live test in February 2027; national real-time feeds for cities missing from the EEA feed (for example Kraków); forecasts read directly from the Copernicus Atmosphere Data Store. |

## Results

Reconstructed scores, last 365 days to 2026-11-13. RMSE is the typical error in µg/m³. Skill is
1 − MSE(forecast) / MSE(persistence): above 0 the forecast is better. The verdict is given only when the 95% interval
of the skill score does not include 0.

| Verdict | Cities |
|---|---|
| Forecast clearly better (9) | Helsinki, Tampere, Oulu, Malmö, Paris, Lyon, Marseille, Toulouse, Gdańsk |
| No clear difference (12) | Basel, Lugano, Zürich, Bordeaux, Strasbourg, Bolzano, Brescia, Roma, Bergen, Wrocław, Łódź, Göteborg |
| Persistence clearly better (7) | Katowice, Warszawa, Milano, Torino, Napoli, Grenoble, Annecy |

Examples (forecast error vs persistence error, µg/m³): Lyon 3.7 vs 5.6; Helsinki 2.6 vs 3.9; Gdańsk 6.4 vs 7.9;
Warszawa 10.2 vs 7.7; Milano 17.3 vs 9.7; Katowice 18.8 vs 6.5. All numbers for every city are in the
[panel](https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html) and in
[`docs/showcase/aircheck_data.json`](docs/showcase/aircheck_data.json).

### Negative and inconclusive results

- In 7 of 28 cities the forecast is clearly worse than the simplest rule, mostly where winter fine dust is high
  (southern Poland, the Po Valley) and in two Alpine valleys.
- For days above 25 µg/m³ the forecast does not catch high-dust days better than persistence in several cities
  (for example Warszawa 0.41 vs 0.48, Milano 0.54 vs 0.65, critical success index).
- The cause of the winter over-forecast was not investigated. It is reported as measured.
- Forecast skill before November 2023 cannot be checked: the forecast archive starts there. The CAMS reanalysis for
  earlier years is not used as evidence, because it takes in measurements from the same stations
  (correlation 0.98–0.99 in a trial run).
- 19 of 47 candidate cities are not in the registry: no urban background station with PM2.5 in both the verified
  and the up-to-date EEA feed, or too many missing days. The list with reasons is in
  [`aircheck/stations.csv`](aircheck/stations.csv). Kraków, København, Stockholm and Oslo are among them.

## Method

1. **Stations.** One urban or suburban background station per city, chosen by a written rule: within 15 km
   (20 km for large cities), PM2.5 in both EEA feeds, at least 75% of days in every year since 2022
   ([`aircheck/registry.py`](aircheck/registry.py)).
2. **Measurement.** Daily mean in UTC from at least 18 valid hours, or the daily value reported by the network.
   Days with a stuck sensor (at most two different values) are dropped.
3. **Forecast.** CAMS ensemble, daily mean in UTC at the station location. The forecast issued today is saved with
   its issue date and never changed. Archived forecasts (lead below one day) are used for the reconstruction.
4. **Scores.** RMSE of the forecast and of persistence, skill score with a 95% interval (block bootstrap, 7-day
   blocks), and hits, misses and false alarms for days above 25 µg/m³.
5. **Data quality gate.** If fewer than half of the stations have a fresh measurement, or today's forecast is
   missing, the panel is not updated and the run fails with an issue.
6. **Confirmation test.** Protocol [A1](docs/evidence/A1_protokol_prognozy.md) (in Polish) fixes the window, the
   scores and the decision rules before the first test day. Its SHA-256 is stored in the code and checked in CI.

## Code

| Path | Content |
|---|---|
| [`aircheck/`](aircheck/) | package: `sources/` (EEA, CAMS), `core.py` (scores), `pipeline.py`, `publish.py`, `registry.py`, `selftest.py` |
| [`aircheck/stations.csv`](aircheck/stations.csv) | station registry with data completeness per year |
| [`data/`](data/) | pipeline state: daily measurements and forecasts as small CSV tables |
| [`docs/showcase/`](docs/showcase/) | published result: panel, data, map points, run status |
| [`docs/`](docs/) | documentation in Polish: status and plan, architecture, how to run, step-by-step guide, protocol |
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

`selftest` needs no network (about a minute). `run` does what the daily job does. Other commands: `backfill`
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
