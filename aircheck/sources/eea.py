"""Pomiary PM2.5 ze stacji: Europejska Agencja Środowiska (EEA), Air Quality Download Service.

Zbiory: 2 = dane zweryfikowane (E1a, zwykle do końca poprzedniego roku), 1 = dane bieżące, niezweryfikowane (UTD).
Jeden plik parquet na punkt pomiarowy. Czas w plikach EEA jest w UTC+1; przed liczeniem średniej dobowej
przesuwamy go do UTC (ta sama doba co w prognozie).
"""

from __future__ import annotations

import io
import re
import time
from typing import Dict, Optional

import pandas as pd
import requests

API = "https://eeadmz1-downloads-api-appservice.azurewebsites.net/ParquetFile/urls"
METADATA_URL = "https://discomap.eea.europa.eu/App/AQViewer/download?fqn=Airquality_Dissem.b2g.measurements&f=csv"
VERIFIED, UTD = 2, 1
MIN_HOURS = 18          # doba liczy się przy co najmniej 18 ważnych godzinach
STUCK_UNIQUE = 2        # zacięty czujnik: najwyżej 2 różne wartości w dobie przy >= 18 godzinach
MAX_VALUE = 2000.0      # µg/m³; wartości powyżej traktujemy jako błąd zapisu
COLUMNS = ["pm25", "n", "stuck"]


def norm_id(sampling_point: str) -> str:
    """Identyfikator punktu pomiarowego bez znaków specjalnych (nazwy plików i metadane różnią się zapisem)."""
    return re.sub("[^A-Z0-9]", "", str(sampling_point).upper())


def file_urls(country: str, dataset: int, pollutant: str = "PM2.5", retries: int = 3) -> Dict[str, str]:
    """Słownik: znormalizowany identyfikator punktu pomiarowego -> adres pliku parquet."""
    body = {"countries": [country], "cities": [], "pollutants": [pollutant], "dataset": dataset, "source": "API"}
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            r = requests.post(API, json=body, timeout=120)
            r.raise_for_status()
            urls = [u.strip() for u in r.text.splitlines()[1:] if u.strip()]
            return {norm_id(u.rsplit("/", 1)[1].replace(".parquet", "")): u for u in urls}
        except Exception as e:  # sieć bywa zawodna; próbujemy ponownie
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"EEA: lista plików {country}/{dataset} niedostępna: {last}")


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS, index=pd.DatetimeIndex([], name="date"))


def daily_from_frame(d: pd.DataFrame, min_hours: int = MIN_HOURS) -> pd.DataFrame:
    """Średnie dobowe (UTC) z tabeli EEA. Kolumny: pm25, n (liczba godzin; 24 dla wartości dobowych), stuck."""
    if d is None or d.empty:
        return _empty()
    d = d[(d["Validity"] >= 1) & (d["Value"] >= 0) & (d["Value"] <= MAX_VALUE)]
    parts = []
    h = d[d["AggType"] == "hour"]
    if len(h):
        s = pd.Series(h["Value"].astype(float).values, index=pd.to_datetime(h["Start"].values) - pd.Timedelta(hours=1))
        s = s[~s.index.duplicated()].sort_index()
        g = s.groupby(s.index.normalize())
        x = pd.DataFrame({"pm25": g.mean(), "n": g.count(), "uniq": g.nunique()})
        x["stuck"] = (x["uniq"] <= STUCK_UNIQUE) & (x["n"] >= min_hours) & (x["pm25"] > 0)
        parts.append(x[x["n"] >= min_hours][COLUMNS])
    dd = d[d["AggType"] == "day"]
    if len(dd):
        s = pd.Series(dd["Value"].astype(float).values, index=pd.to_datetime(dd["Start"].values).normalize())
        s = s[~s.index.duplicated()].sort_index()
        parts.append(pd.DataFrame({"pm25": s, "n": 24, "stuck": False}))
    if not parts:
        return _empty()
    out = pd.concat(parts)
    out = out[~out.index.duplicated(keep="first")].sort_index()   # pierwsze = z godzin, gdy są oba rodzaje
    out.index.name = "date"
    return out


def read_daily(url: str, retries: int = 3) -> pd.DataFrame:
    """Pobiera jeden plik punktu pomiarowego i zwraca średnie dobowe."""
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            d = pd.read_parquet(io.BytesIO(r.content), columns=["Start", "Value", "Validity", "AggType"])
            d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
            return daily_from_frame(d)
        except Exception as e:
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"EEA: plik niedostępny {url}: {last}")
