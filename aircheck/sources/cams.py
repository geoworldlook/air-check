"""Prognoza PM2.5: zespół modeli CAMS (Copernicus Atmosphere Monitoring Service), siatka ok. 10 km, Europa.

Dostęp przez Open-Meteo Air Quality API (bez klucza; warunki: użytek niekomercyjny, wymagane podanie źródła).
Dwa tryby:
  archive(...)  prognozy zarchiwizowane u dostawcy (od X 2023), wyprzedzenie poniżej doby: do rekonstrukcji;
  live(...)     prognoza wydana dziś na dziś i 3 kolejne dni: zapisujemy ją z datą wydania, żeby potem ocenić
                prognozę na jutro dokładnie taką, jaka była dostępna.
Średnia dobowa liczona w UTC z co najmniej 18 godzin.
"""

from __future__ import annotations

import time
from typing import List, Optional

import pandas as pd
import requests

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
META = "https://air-quality-api.open-meteo.com/data/cams_europe/static/meta.json"
MIN_HOURS = 18
CHUNK = 10
COLUMNS = ["date", "station", "pm25"]


WAITS = (15, 30, 60, 90, 120)      # sekundy między próbami; limit minutowy dostawcy odnawia się po 60 s


def _get(params: dict, waits=WAITS) -> list:
    """Zapytanie z ponawianiem. Serwery GitHub Actions dzielą adres IP z innymi, więc limit zapytań (429)
    zdarza się bez naszej winy; czekamy cierpliwie, a przebieg jest powtarzany kilka razy dziennie."""
    last: Optional[Exception] = None
    for wait in (*waits, None):
        try:
            r = requests.get(URL, params=params, timeout=180)
            if r.status_code == 429:
                raise RuntimeError("limit zapytań (429)")
            r.raise_for_status()
            j = r.json()
            return j if isinstance(j, list) else [j]
        except Exception as e:
            last = e
            if wait is not None:
                time.sleep(wait)
    raise RuntimeError(f"Open-Meteo niedostępne: {last}")


def daily_mean(times: List[str], values: List[Optional[float]]) -> pd.Series:
    """Średnia dobowa (UTC) z szeregu godzinowego; doba liczy się przy co najmniej MIN_HOURS wartościach."""
    s = pd.Series(values, index=pd.to_datetime(times), dtype="float64").dropna()
    if s.empty:
        return pd.Series(dtype="float64")
    g = s.groupby(s.index.normalize())
    m = g.mean()[g.count() >= MIN_HOURS]
    m.index.name = "date"
    return m


def _fetch(stations: pd.DataFrame, extra: dict) -> pd.DataFrame:
    rows = []
    for i in range(0, len(stations), CHUNK):
        part = stations.iloc[i:i + CHUNK]
        params = dict(latitude=",".join(f"{v:.5f}" for v in part["lat"]),
                      longitude=",".join(f"{v:.5f}" for v in part["lon"]),
                      hourly="pm2_5", domains="cams_europe", timezone="UTC", **extra)
        for sid, j in zip(part["id"], _get(params)):
            m = daily_mean(j["hourly"]["time"], j["hourly"]["pm2_5"])
            rows.append(pd.DataFrame({"date": m.index, "station": sid, "pm25": m.round(2).values}))
        time.sleep(1.0)
    return pd.concat(rows, ignore_index=True)[COLUMNS] if rows else pd.DataFrame(columns=COLUMNS)


def _year_chunks(start: str, end: str):
    a, e = pd.Timestamp(start), pd.Timestamp(end)
    while a <= e:
        b = min(e, pd.Timestamp(year=a.year, month=12, day=31))
        yield a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")
        a = b + pd.Timedelta(days=1)


def archive(stations: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Średnie dobowe z archiwum prognoz dla okresu [start, end]. Kolumny: date, station, pm25."""
    out = [_fetch(stations, dict(start_date=a, end_date=b)) for a, b in _year_chunks(start, end)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=COLUMNS)


def live(stations: pd.DataFrame, days: int = 4) -> pd.DataFrame:
    """Prognoza wydana dziś: średnie dobowe na dziś i kolejne dni. Kolumny: date (dzień docelowy), station, pm25."""
    return _fetch(stations, dict(forecast_days=days))


def model_run() -> Optional[str]:
    """Czas startu ostatniego przebiegu modelu u dostawcy (UTC, ISO) albo None."""
    try:
        j = requests.get(META, timeout=60).json()
        t = j.get("last_run_initialisation_time")
        return pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%MZ") if t else None
    except Exception:
        return None
