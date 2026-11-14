"""Rejestr stacji (aircheck/stations.csv) i jego budowa z metadanych EEA.

Reguła wyboru (zapisana, powtarzalna): dla każdego miasta z CITIES bierzemy punkty pomiarowe PM2.5 w promieniu
RADIUS_KM od centrum, typu „background”, w obszarze miejskim lub podmiejskim, które mają plik w zbiorze
zweryfikowanym i w zbiorze bieżącym. Wygrywa stacja o najwyższej najmniejszej rocznej kompletności dni
(2022 – bieżący rok). Miasto wchodzi do rejestru, gdy ta kompletność wynosi co najmniej MIN_COVERAGE procent.
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests

from .sources import eea

STATIONS_CSV = Path(__file__).resolve().parent / "stations.csv"
RADIUS_KM, RADIUS_BIG_KM, MIN_COVERAGE, MAX_CANDIDATES = 15.0, 20.0, 75, 6
ISO = {"PL": "Poland", "IT": "Italy", "FR": "France", "CH": "Switzerland", "NO": "Norway", "SE": "Sweden",
       "DK": "Denmark", "FI": "Finland"}
# (kraj, miasto, szerokość, długość, duża aglomeracja)
CITIES: List[Tuple[str, str, float, float, bool]] = [
    ("PL", "Warszawa", 52.23, 21.01, True), ("PL", "Kraków", 50.06, 19.94, False),
    ("PL", "Katowice", 50.26, 19.02, True), ("PL", "Rybnik", 50.10, 18.54, False),
    ("PL", "Wrocław", 51.11, 17.03, False), ("PL", "Poznań", 52.41, 16.93, False),
    ("PL", "Gdańsk", 54.35, 18.65, False), ("PL", "Łódź", 51.76, 19.46, False),
    ("PL", "Nowy Sącz", 49.62, 20.69, False),
    ("IT", "Milano", 45.46, 9.19, True), ("IT", "Torino", 45.07, 7.69, False),
    ("IT", "Bologna", 44.49, 11.34, False), ("IT", "Venezia", 45.48, 12.25, False),
    ("IT", "Padova", 45.41, 11.88, False), ("IT", "Brescia", 45.54, 10.22, False),
    ("IT", "Roma", 41.90, 12.50, True), ("IT", "Napoli", 40.85, 14.27, True),
    ("IT", "Bolzano", 46.50, 11.35, False), ("IT", "Firenze", 43.77, 11.26, False),
    ("FR", "Paris", 48.86, 2.35, True), ("FR", "Lyon", 45.76, 4.84, True),
    ("FR", "Marseille", 43.30, 5.37, True), ("FR", "Grenoble", 45.19, 5.72, False),
    ("FR", "Strasbourg", 48.58, 7.75, False), ("FR", "Toulouse", 43.60, 1.44, False),
    ("FR", "Lille", 50.63, 3.06, False), ("FR", "Bordeaux", 44.84, -0.58, False),
    ("FR", "Annecy", 45.90, 6.13, False),
    ("CH", "Zürich", 47.38, 8.54, False), ("CH", "Basel", 47.56, 7.59, False),
    ("CH", "Bern", 46.95, 7.45, False), ("CH", "Lugano", 46.00, 8.95, False),
    ("NO", "Oslo", 59.91, 10.75, True), ("NO", "Bergen", 60.39, 5.32, False),
    ("NO", "Trondheim", 63.43, 10.40, False), ("NO", "Stavanger", 58.97, 5.73, False),
    ("NO", "Tromsø", 69.65, 18.96, False),
    ("SE", "Stockholm", 59.33, 18.07, True), ("SE", "Göteborg", 57.71, 11.97, False),
    ("SE", "Malmö", 55.60, 13.00, False), ("SE", "Umeå", 63.83, 20.26, False),
    ("SE", "Uppsala", 59.86, 17.64, False),
    ("DK", "København", 55.68, 12.57, True), ("DK", "Aarhus", 56.16, 10.20, False),
    ("FI", "Helsinki", 60.17, 24.94, True), ("FI", "Tampere", 61.50, 23.76, False),
    ("FI", "Oulu", 65.01, 25.47, False),
]


def load(path: Path | None = None) -> pd.DataFrame:
    """Rejestr stacji używany przez potok (tylko stacje przyjęte)."""
    d = pd.read_csv(path or STATIONS_CSV, encoding="utf-8")
    return d[d["status"] == "accepted"].reset_index(drop=True)


def _km(lat1: float, lon1: float, lat2, lon2):
    return np.hypot((lat2 - lat1) * 111.2, (lon2 - lon1) * 111.2 * np.cos(np.radians(lat1)))


def coverage(index: pd.DatetimeIndex, today: dt.date, first_year: int = 2022) -> Dict[int, int]:
    """Procent dni z pomiarem w każdym roku (bieżący rok: do dziś)."""
    cov = {}
    for y in range(first_year, today.year + 1):
        days = (min(today, dt.date(y, 12, 31)) - dt.date(y, 1, 1)).days + 1
        cov[y] = int(round(100 * int((index.year == y).sum()) / days))
    return cov


def build(today: dt.date | None = None, log=print) -> pd.DataFrame:
    """Buduje propozycję rejestru z metadanych EEA (sieć, kilka minut). Nie zapisuje pliku."""
    today = today or dt.date.today()
    z = zipfile.ZipFile(io.BytesIO(requests.get(eea.METADATA_URL, timeout=300).content))
    m = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
    m = m[m["Air Pollutant"] == "PM2.5"].copy()
    m["key"] = m["Sampling Point Id"].map(eea.norm_id)
    m = m.drop_duplicates("key").set_index("key")
    urls: Dict[Tuple[str, int], Dict[str, str]] = {}
    rows = []
    for cc, city, lat, lon, big in CITIES:
        for ds in (eea.VERIFIED, eea.UTD):
            if (cc, ds) not in urls:
                urls[(cc, ds)] = eea.file_urls(cc, ds)
        mm = m[m["Country"] == ISO[cc]].copy()
        mm["km"] = _km(lat, lon, mm["Latitude"].astype(float), mm["Longitude"].astype(float))
        radius = RADIUS_BIG_KM if big else RADIUS_KM
        near = mm[mm["km"] <= radius]
        cand = near[(near["Air Quality Station Type"] == "background")
                    & near["Air Quality Station Area"].isin(["urban", "suburban"])].sort_values("km")
        best = None
        # Stacja może mieć osobny punkt pomiarowy w danych zweryfikowanych (np. metoda wagowa, wartości dobowe)
        # i osobny w danych bieżących (analizator automatyczny). Dla każdego zbioru bierzemy punkt z największą liczbą dni.
        for code in list(dict.fromkeys(cand["Air Quality Station EoI Code"]))[:MAX_CANDIDATES]:
            pts = cand[cand["Air Quality Station EoI Code"] == code]
            r = pts.iloc[0]
            picked = {}
            for ds, years in ((eea.VERIFIED, range(2022, today.year)), (eea.UTD, [today.year])):
                top = None
                for key in pts.index:
                    if key not in urls[(cc, ds)]:
                        continue
                    try:
                        s = eea.read_daily(urls[(cc, ds)][key])
                    except Exception as e:
                        log(f"  {city}: {key} pominięty ({e})")
                        continue
                    s = s[~s["stuck"].astype(bool)]
                    n = int(s.index.year.isin(list(years)).sum())
                    if top is None or n > top[0]:
                        top = (n, key, s)
                if top:
                    picked[ds] = top
            if eea.UTD not in picked or eea.VERIFIED not in picked:
                continue
            s = pd.concat([picked[eea.VERIFIED][2], picked[eea.UTD][2]])
            s = s[~s.index.duplicated()].sort_index()
            cov = coverage(s.index, today)
            score = min(cov.values())
            kv, ku = picked[eea.VERIFIED][1], picked[eea.UTD][1]
            rec = dict(id=code, country=cc, city=city, name=str(r["Air Quality Station Name"]).strip('"'),
                       sampling_point=f"{pts.loc[kv, 'Sampling Point Id']} | {pts.loc[ku, 'Sampling Point Id']}",
                       lat=round(float(r["Latitude"]), 5), lon=round(float(r["Longitude"]), 5),
                       area=r["Air Quality Station Area"], type=r["Air Quality Station Type"],
                       km_from_centre=round(float(r["km"]), 1), **{f"cov{y}": c for y, c in cov.items()}, min_cov=score,
                       url_verified=urls[(cc, eea.VERIFIED)][kv], url_utd=urls[(cc, eea.UTD)][ku])
            if best is None or score > best["min_cov"]:
                best = rec
            if score >= 90:
                break
        if best is None:
            rows.append(dict(id="", country=cc, city=city, name="", status="excluded",
                             reason=f"brak stacji tła z danymi w promieniu {radius:.0f} km (kandydatów {len(cand)})"))
            log(f"{cc} {city}: brak")
            continue
        ok = best["min_cov"] >= MIN_COVERAGE
        best["status"] = "accepted" if ok else "excluded"
        best["reason"] = "" if ok else f"kompletność {best['min_cov']}% < {MIN_COVERAGE}%"
        rows.append(best)
        log(f"{cc} {city}: {best['id']} {best['name']} ({best['km_from_centre']} km) min {best['min_cov']}% "
            f"-> {best['status']}")
    return pd.DataFrame(rows)
