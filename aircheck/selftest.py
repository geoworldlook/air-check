"""Test bez sieci i bez kluczy: dane syntetyczne, cały potok dwa razy (dwa kolejne dni), bramka jakości,
testy jednostkowe modułów. To samo uruchamia CI przy każdej zmianie kodu.

    python -m aircheck selftest
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, core, pipeline, registry
from .sources import cams, eea

TODAY = dt.date(2026, 11, 14)
STATIONS = pd.DataFrame([
    dict(id="XX0001A", country="PL", city="Dobre", name="Test good", lat=52.0, lon=21.0, status="accepted"),
    dict(id="XX0002A", country="IT", city="Zle", name="Test bad", lat=45.0, lon=9.0, status="accepted"),
    dict(id="XX0003A", country="FR", city="Srednie", name="Test noisy", lat=48.0, lon=2.0, status="accepted"),
    dict(id="XX0004A", country="SE", city="Czyste", name="Test clean", lat=59.0, lon=18.0, status="accepted"),
])
FC_NOISE = {"XX0001A": 2.0, "XX0002A": 30.0, "XX0003A": 3.0, "XX0004A": 1.0}   # błąd reguły to ok. 4,4 µg/m³


def _truth(sid: str, days: pd.DatetimeIndex) -> np.ndarray:
    """Syntetyczny pył: sezon zimowy + powolne epizody + szum. Stały dla danej stacji i dnia."""
    k = int(sid[2:6])
    doy = days.dayofyear.to_numpy()
    base = (18 if k < 4 else 4) + (12 if k < 4 else 1) * np.cos(2 * np.pi * (doy - 15) / 365.25)
    n = days.to_julian_date().to_numpy().astype(int)
    slow = 6 * np.sin(n / 5.0 + k) + 4 * np.sin(n / 13.0 + 2 * k)
    noise = np.array([np.random.default_rng(1000 * k + int(v)).normal(0, 3) for v in n])
    return np.clip(base + slow + noise, 0.5, None)


def _fc(sid: str, days: pd.DatetimeIndex, salt: int) -> np.ndarray:
    n = days.to_julian_date().to_numpy().astype(int)
    k = int(sid[2:6])
    err = np.array([np.random.default_rng(7919 * k + 31 * salt + int(v)).normal(0, FC_NOISE[sid]) for v in n])
    return np.clip(_truth(sid, days) + err, 0.1, None)


class FakeSources(pipeline.Sources):
    """Atrapa źródeł: te same metody co Sources, bez sieci. `today` przesuwa się między przebiegami."""

    def __init__(self, today: dt.date, stale: bool = False):
        self.today, self.stale = today, stale

    def _obs(self, sid: str, a: str, b: str) -> pd.DataFrame:
        days = pd.date_range(a, b)
        d = pd.DataFrame({"pm25": _truth(sid, days), "n": 24, "stuck": False}, index=days)
        d.index.name = "date"
        if len(d) > 40:
            d.iloc[40, d.columns.get_loc("stuck")] = True       # jeden dzień z zaciętym czujnikiem
        return d

    def obs_verified(self, st):
        return self._obs(st["id"], "2022-01-01", "2025-12-31")

    def obs_utd(self, st):
        last = self.today - dt.timedelta(days=30 if self.stale else 1)
        return self._obs(st["id"], "2026-01-01", last.isoformat())

    def fc_archive(self, stations, start, end):
        days = pd.date_range(start, end)
        return pd.concat([pd.DataFrame({"date": days, "station": s, "pm25": _fc(s, days, 0)}) for s in stations["id"]],
                         ignore_index=True)

    def fc_live(self, stations):
        days = pd.date_range(self.today, periods=4)
        return pd.concat([pd.DataFrame({"date": days, "station": s, "pm25": _fc(s, days, 1)}) for s in stations["id"]],
                         ignore_index=True)

    def model_run(self):
        return f"{self.today}T00:00Z"


def check(cond: bool, what: str) -> None:
    if not cond:
        raise AssertionError(what)
    print("  ok:", what)


def unit_tests() -> None:
    print("testy jednostkowe")
    # EEA: godziny w UTC+1 -> doba UTC; doba z 18 godzinami wchodzi, z 17 nie; zacięty czujnik oznaczony
    t = pd.date_range("2026-01-01 01:00", periods=24 * 4, freq="h")          # UTC+1, czyli doby UTC 1-4 stycznia
    v = np.r_[np.full(24, 10.0), np.arange(24) + 1.0, np.full(24, 7.0), np.arange(24) + 5.0]
    f = pd.DataFrame({"Start": t, "Value": v, "Validity": 1, "AggType": "hour"})
    f.loc[30:36, "Validity"] = -1                                            # doba 2: 17 ważnych godzin
    d = eea.daily_from_frame(f)
    check(list(d.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-03", "2026-01-04"], "EEA: doby UTC i próg 18 godzin")
    check(bool(d.loc["2026-01-01", "stuck"]) and not bool(d.loc["2026-01-04", "stuck"]), "EEA: zacięty czujnik oznaczony")
    check(abs(d.loc["2026-01-04", "pm25"] - 16.5) < 1e-9, "EEA: średnia dobowa")
    dd = pd.DataFrame({"Start": pd.to_datetime(["2025-03-01", "2025-03-02"]), "Value": [12.0, -5.0], "Validity": [1, 1],
                       "AggType": "day"})
    check(len(eea.daily_from_frame(dd)) == 1, "EEA: wartości dobowe, ujemne odrzucone")
    check(eea.norm_id("SPO.IT1692A_6001_BETA") == "SPOIT1692A6001BETA", "EEA: normalizacja identyfikatora")
    # CAMS: średnia dobowa z godzin
    times = [f"2026-05-01T{h:02d}:00" for h in range(24)] + [f"2026-05-02T{h:02d}:00" for h in range(10)]
    m = cams.daily_mean(times, [float(h) for h in range(24)] + [1.0] * 10)
    check(len(m) == 1 and abs(m.iloc[0] - 11.5) < 1e-9, "CAMS: średnia dobowa i niepełna doba pominięta")
    check(list(cams._year_chunks("2023-11-01", "2025-02-01")) ==
          [("2023-11-01", "2023-12-31"), ("2024-01-01", "2024-12-31"), ("2025-01-01", "2025-02-01")], "CAMS: podział na lata")
    # miary
    days = pd.date_range("2026-01-01", periods=6)
    o = pd.Series([10, 30, 20, 40, 10, 30.0], index=days)
    x = core.paired(o, pd.Series([12, 28, 26, 30, 12, 20.0], index=days))
    check(len(x) == 5 and list(x["p"]) == [10, 30, 20, 40, 10], "pary: reguła „jutro jak dziś” to pomiar z dnia D-1")
    s = core.scores(x, 25.0)
    check(s["exceed_days"] == 3 and s["hits"] == 2 and s["misses"] == 1 and s["false_alarms"] == 1, "trafienia i fałszywe alarmy")
    check(abs(s["rmse_fc"] - (244 / 5) ** 0.5) < 0.01 and abs(s["skill"] - (1 - 244 / 2200)) < 0.001, "RMSE i skill")
    check(core.wilson(8, 10) == (0.49, 0.943), "przedział Wilsona")
    big = core.paired(pd.Series(_truth("XX0001A", pd.date_range("2025-01-01", periods=300)), index=pd.date_range("2025-01-01", periods=300)),
                      pd.Series(_fc("XX0001A", pd.date_range("2025-01-01", periods=300), 0), index=pd.date_range("2025-01-01", periods=300)))
    a, b = core.skill_ci(big, 7, 200, 1), core.skill_ci(big, 7, 200, 1)
    check(a == b and a[0] < a[1], "bootstrap blokowy powtarzalny")
    check(registry.coverage(pd.date_range("2022-01-01", "2022-12-31"), dt.date(2023, 7, 1)) == {2022: 100, 2023: 0},
          "kompletność roczna")


def repo_checks() -> None:
    print("pliki repozytorium")
    st = pd.read_csv(registry.STATIONS_CSV, encoding="utf-8")
    acc = st[st["status"] == "accepted"]
    check(len(acc) >= 20 and acc["id"].is_unique, f"rejestr: {len(acc)} stacji przyjętych, identyfikatory unikalne")
    check(acc["lat"].between(35, 72).all() and acc["lon"].between(-11, 32).all(), "rejestr: współrzędne w Europie")
    check(acc["url_verified"].str.startswith("https://").all() and acc["url_utd"].str.startswith("https://").all(),
          "rejestr: adresy plików")
    check((acc["min_cov"] >= registry.MIN_COVERAGE).all(), "rejestr: kompletność według reguły")
    proto = config.ROOT / config.PROTOCOL
    sha = hashlib.sha256(proto.read_bytes()).hexdigest()
    check(sha == config.PROTOCOL_SHA256, "protokół A1 niezmieniony od zapisania (SHA-256)")


def pipeline_test(work: Path) -> None:
    print("potok na danych syntetycznych:", work)
    quiet = lambda *_: None  # noqa: E731
    rc = pipeline.run(work, TODAY, backfill=True, sources=FakeSources(TODAY), stations=STATIONS, log=quiet)
    check(rc == 0, "przebieg 1 (rekonstrukcja): kod 0")
    day2 = TODAY + dt.timedelta(days=1)
    rc = pipeline.run(work, day2, sources=FakeSources(day2), stations=STATIONS, log=quiet)
    check(rc == 0, "przebieg 2 (kolejny dzień): kod 0")
    P = config.paths(work)
    for name in ("aircheck_panel.html", "aircheck_data.json", "map_points.geojson", "status.json"):
        check((P.showcase / name).exists(), f"plik {name}")
    data = json.loads((P.showcase / "aircheck_data.json").read_text(encoding="utf-8"))
    by = {s["id"]: s for s in data["stations"]}
    check(len(by) == 4 and data["gate"]["passed"], "4 stacje, bramka przeszła")
    check(by["XX0001A"]["archive_365"]["verdict"] == "better", "dobra prognoza -> better")
    check(by["XX0002A"]["archive_365"]["verdict"] == "worse", "zła prognoza -> worse")
    check(by["XX0001A"]["forecast"]["tomorrow"] is not None and by["XX0001A"]["forecast"]["issued"] == day2.isoformat(),
          "prognoza na jutro z dzisiejszego wydania")
    check(by["XX0001A"]["live"]["n"] == 0 and data["test"]["H-A1"]["status"] == "in progress", "test na żywo w toku")
    check(by["XX0001A"]["qc"]["stuck_days"] == 2 and by["XX0001A"]["years"][0]["year"] == 2022, "kontrola jakości i lata od 2022")
    live = pipeline.read_table(P.forecast, "live", ["issue_date", "date"])
    check(len(live) == 2 * 4 * 4 and set(live["lead"]) == {0, 1, 2, 3}, "prognozy na żywo: 2 wydania, wyprzedzenie 0-3 dni")
    obs = pipeline.read_table(P.obs, "obs", ["date"])
    check(not obs.duplicated(["date", "station"]).any() and set(obs["src"]) == {"verified", "utd"}, "pomiary bez duplikatów")
    html = (P.showcase / "aircheck_panel.html").read_text(encoding="utf-8")
    check("XX0001A" in html and "/*DATA*/" not in html and "leaflet" in html.lower(), "panel zawiera dane i mapę")
    geo = json.loads((P.showcase / "map_points.geojson").read_text(encoding="utf-8"))
    check(len(geo["features"]) == 4 and geo["features"][0]["properties"]["title"].startswith("Air Check"), "punkty mapy")
    # trzeci przebieg po 80 dniach na żywo: prognoza D+1 dobrej stacji ma werdykt, test ma policzone stacje
    src = FakeSources(TODAY)
    for i in range(2, 100):
        d = TODAY + dt.timedelta(days=i)
        src.today = d
        pipeline.update_live(STATIONS, P, src, d, quiet)
    end = TODAY + dt.timedelta(days=99)
    rc = pipeline.run(work, end, sources=FakeSources(end), stations=STATIONS, log=quiet)
    data = json.loads((P.showcase / "aircheck_data.json").read_text(encoding="utf-8"))
    by = {s["id"]: s for s in data["stations"]}
    check(rc == 0 and by["XX0001A"]["live"]["n"] >= 90, "po 100 dniach: pary prognozy na jutro policzone")
    check(data["test"]["final"] and data["test"]["H-A1"]["stations"] == 4 and data["test"]["H-A1"]["better"] == 3,
          "test potwierdzający zamknięty: 3 z 4 stacji lepsze")
    check(data["test"]["H-A1"]["status"] == "confirmed", "H-A1 potwierdzona na danych syntetycznych (3/4 >= 2/3)")
    # bramka jakości: nieświeże pomiary zatrzymują publikację i nie ruszają panelu
    before = (P.showcase / "aircheck_data.json").read_bytes()
    late = end + dt.timedelta(days=40)
    rc = pipeline.run(work, late, sources=FakeSources(late, stale=True), stations=STATIONS, log=quiet)
    check(rc == 2 and (P.showcase / "aircheck_data.json").read_bytes() == before, "bramka jakości zatrzymała publikację")
    last = json.loads((P.logs / "last_run.json").read_text(encoding="utf-8"))
    check(last["status"] == "gate_failed", "stan przebiegu: gate_failed")
    check(pipeline.render(work, end, stations=STATIONS, log=quiet) == 0, "render z zapisanych tabel")


def main() -> int:
    try:
        unit_tests()
        repo_checks()
        with tempfile.TemporaryDirectory(prefix="aircheck_selftest_") as tmp:
            pipeline_test(Path(tmp))
    except AssertionError as e:
        print("SELFTEST: BŁĄD:", e)
        return 1
    print("SELFTEST: OK")
    return 0
