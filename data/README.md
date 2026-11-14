# Data in this folder

Small derived tables that are the state of the pipeline. Raw files are not stored here.

| File | Content | Source |
|---|---|---|
| `obs/obs_YYYY.csv` | daily mean PM2.5 per station (µg/m³), hours used, source flag | European Environment Agency (EEA), Air Quality e-Reporting: verified data (E1a) and up-to-date data (UTD), reported by the national networks |
| `forecast/archive_YYYY.csv` | daily mean of archived CAMS forecasts at the station location | Copernicus Atmosphere Monitoring Service (CAMS) European air quality forecasts, via the Open-Meteo Air Quality API |
| `forecast/live_YYYY.csv` | daily mean of the forecast saved on its issue date, lead 0–3 days | same |

## Attribution

- **Measurements:** European Environment Agency (EEA). EEA content is published under CC BY 4.0 unless stated
  otherwise; the measurements are reported to the EEA by the national air-quality networks. Current-year (UTD)
  values are preliminary and not yet verified by the networks.
- **Forecast:** Generated using Copernicus Atmosphere Monitoring Service information. CAMS European air quality
  forecasts are distributed under the CC-BY licence (Atmosphere Data Store). Neither the European Commission nor ECMWF
  is responsible for any use of this information.
- **Access:** forecast values are retrieved through the Open-Meteo Air Quality API (open-meteo.com), which is free
  for non-commercial use and requires attribution.

The daily means in these tables are computed by Air Check (`aircheck/sources/`), so they are modified data.
