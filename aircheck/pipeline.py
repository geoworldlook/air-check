"""Potok Air Check: pomiary -> prognozy -> bramka jakości -> miary -> publikacja.

Stan potoku to małe tabele CSV w data/ (jeden plik na rok), więc przebieg w GitHub Actions nie potrzebuje
żadnego dysku poza repozytorium:
  data/obs/obs_RRRR.csv            date, station, pm25, n, src (verified | utd), stuck
  data/forecast/archive_RRRR.csv   date, station, pm25                    prognozy z archiwum (rekonstrukcja)
  data/forecast/live_RRRR.csv      issue_date, date, lead, station, pm25, model_run   prognozy zapisane w dniu wydania
"""

from __future__ import annotations

import datetime as dt
import json
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from . import config, core, correct, publish, registry
from .sources import cams, eea


class Sources:
    """Dostęp do sieci. Test bez sieci podstawia własny obiekt z tymi samymi metodami."""

    def obs_verified(self, st: pd.Series) -> pd.DataFrame:
        return eea.read_daily(st["url_verified"])

    def obs_utd(self, st: pd.Series) -> pd.DataFrame:
        return eea.read_daily(st["url_utd"])

    def fc_archive(self, stations: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        return cams.archive(stations, start, end)

    def fc_live(self, stations: pd.DataFrame) -> pd.DataFrame:
        return cams.live(stations)

    def model_run(self) -> Optional[str]:
        return cams.model_run()


# ---------------------------------------------------------------- tabele CSV (jeden plik na rok)

def read_table(folder: Path, prefix: str, date_cols: List[str]) -> pd.DataFrame:
    files = sorted(folder.glob(f"{prefix}_*.csv"))
    if not files:
        return pd.DataFrame()
    d = pd.concat([pd.read_csv(f, encoding="utf-8") for f in files], ignore_index=True)
    for c in date_cols:
        d[c] = pd.to_datetime(d[c])
    return d


def write_table(d: pd.DataFrame, folder: Path, prefix: str, year_col: str, sort_cols: List[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    d = d.sort_values(sort_cols)
    for year, part in d.groupby(d[year_col].dt.year):
        out = part.copy()
        for c in out.columns:
            if pd.api.types.is_datetime64_any_dtype(out[c]):
                out[c] = out[c].dt.strftime("%Y-%m-%d")
        out.to_csv(folder / f"{prefix}_{int(year)}.csv", index=False, encoding="utf-8", lineterminator="\n")


# ---------------------------------------------------------------- kroki potoku

def _obs_rows(d: pd.DataFrame, sid: str, src: str) -> pd.DataFrame:
    d = d[d.index >= pd.Timestamp(config.START)]
    return pd.DataFrame({"date": d.index, "station": sid, "pm25": d["pm25"].round(2).values,
                         "n": d["n"].astype(int).values, "src": src, "stuck": d["stuck"].astype(int).values})


def update_obs(st: pd.DataFrame, P: config.Paths, src: Sources, backfill: bool, log: Callable,
               today: dt.date | None = None) -> pd.DataFrame:
    """Pomiary: dane zweryfikowane (raz, przy rekonstrukcji) i bieżące (przy każdym przebiegu).
    Bieżąca doba (UTC) nie jest jeszcze pełna, więc do tabeli wchodzą tylko doby zakończone."""
    old = read_table(P.obs, "obs", ["date"])
    have_verified = set(old.loc[old["src"] == "verified", "station"]) if len(old) else set()
    new, failed = [], []
    for _, s in st.iterrows():
        try:
            if backfill or s["id"] not in have_verified:
                new.append(_obs_rows(src.obs_verified(s), s["id"], "verified"))
            new.append(_obs_rows(src.obs_utd(s), s["id"], "utd"))
        except Exception as e:
            failed.append(s["id"])
            log(f"  pomiary {s['id']} ({s['city']}): błąd: {e}")
    parts = [p for p in new if len(p)] + ([old] if len(old) else [])
    if not parts:
        raise RuntimeError("brak jakichkolwiek pomiarów")
    d = pd.concat(parts, ignore_index=True)
    d["_rank"] = (d["src"] != "verified").astype(int)      # zweryfikowane przed bieżącymi; nowe przed starymi
    d = d.sort_values("_rank", kind="stable").drop_duplicates(["date", "station"], keep="first").drop(columns="_rank")
    d = d[d["station"].isin(set(st["id"]))]
    if today is not None:
        d = d[d["date"] < pd.Timestamp(today)]
    write_table(d, P.obs, "obs", "date", ["date", "station"])
    log(f"pomiary: {len(d)} wierszy, stacji {d['station'].nunique()}, błędów pobrania {len(failed)}")
    return d


def update_archive(st: pd.DataFrame, P: config.Paths, src: Sources, today: dt.date, backfill: bool,
                   log: Callable) -> pd.DataFrame:
    """Prognozy z archiwum dostawcy: całość przy rekonstrukcji, potem ostatnie 10 dni (samonaprawa dziur)."""
    old = read_table(P.forecast, "archive", ["date"])
    end = (today - dt.timedelta(days=1)).isoformat()
    new = []
    known = set(old["station"]) if len(old) else set()
    fresh = st[~st["id"].isin(known)]
    if backfill or old.empty:
        new.append(src.fc_archive(st, config.ARCHIVE_START, end))
    else:
        if len(fresh):
            new.append(src.fc_archive(fresh, config.ARCHIVE_START, end))
        start = (old["date"].max() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        new.append(src.fc_archive(st[st["id"].isin(known)], start, end))
    parts = [p for p in new if len(p)] + ([old] if len(old) else [])
    if not parts:
        raise RuntimeError("brak prognoz z archiwum")
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    d = d.drop_duplicates(["date", "station"], keep="first")
    d = d[d["station"].isin(set(st["id"]))]
    write_table(d, P.forecast, "archive", "date", ["date", "station"])
    log(f"prognozy z archiwum: {len(d)} wierszy, do {d['date'].max().date()}")
    return d


def update_live(st: pd.DataFrame, P: config.Paths, src: Sources, today: dt.date, log: Callable) -> pd.DataFrame:
    """Prognoza wydana dziś, zapisana z datą wydania (issue_date) i wyprzedzeniem w dniach (lead)."""
    old = read_table(P.forecast, "live", ["issue_date", "date"])
    fc = src.fc_live(st)
    if fc.empty:
        raise RuntimeError("brak dzisiejszej prognozy")
    fc["date"] = pd.to_datetime(fc["date"])
    fc["issue_date"] = pd.Timestamp(today)
    fc["lead"] = (fc["date"] - fc["issue_date"]).dt.days
    fc = fc[(fc["lead"] >= 0) & (fc["lead"] <= 3)]
    fc["model_run"] = src.model_run() or ""
    fc = fc[["issue_date", "date", "lead", "station", "pm25", "model_run"]]
    if len(old) and "pm25_corr" not in old:
        old["pm25_corr"] = float("nan")
    fc["pm25_corr"] = float("nan")
    if len(old):                                             # ponowny przebieg tego samego dnia zachowuje zapisaną korektę
        key = ["issue_date", "date", "station"]
        fc = fc.drop(columns="pm25_corr").merge(old[key + ["pm25_corr"]], on=key, how="left")
    d = pd.concat([fc] + ([old] if len(old) else []), ignore_index=True)
    d = d.drop_duplicates(["issue_date", "date", "station"], keep="first")
    d = d[d["station"].isin(set(st["id"]))]
    write_table(d, P.forecast, "live", "issue_date", ["issue_date", "station", "date"])
    log(f"prognoza na żywo: wydanie {today}, wierszy dziś {len(fc)}, razem {len(d)}")
    return d


def _series(obs: pd.DataFrame, arch: pd.DataFrame):
    good = obs[(obs["stuck"] == 0) & obs["pm25"].notna()]
    o_all = good.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    f_arch = arch.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    return o_all, f_arch


def add_live_correction(st: pd.DataFrame, P: config.Paths, obs: pd.DataFrame, arch: pd.DataFrame, live: pd.DataFrame,
                        log: Callable) -> pd.DataFrame:
    """Skorygowana prognoza na jutro (protokół A2), zapisana obok surowej w kolumnie pm25_corr.
    Dla dnia docelowego D regresja używa pomiarów najpóźniej z dnia D-2 (lag = 2), czyli tylko tego, co było znane
    w dniu wydania. Uczy się na prognozach z archiwum; tam, gdzie są już prognozy zapisane na żywo, bierze je."""
    if "pm25_corr" not in live:
        live["pm25_corr"] = float("nan")
    todo = live[(live["lead"] == 1) & live["pm25_corr"].isna()]
    if todo.empty:
        return live
    o_all, f_arch = _series(obs, arch)
    l1 = live[live["lead"] == 1].pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    filled = 0
    for sid in todo["station"].unique():
        if sid not in o_all or sid not in f_arch:
            continue
        idx = pd.date_range(f_arch.index.min(), todo["date"].max())
        f = f_arch[sid].reindex(idx)
        if sid in l1:
            f = l1[sid].reindex(idx).combine_first(f)
        c = correct.mos(o_all[sid].reindex(idx), f, lag=2, window=config.MOS_WINDOW)
        rows = todo[todo["station"] == sid]
        live.loc[rows.index, "pm25_corr"] = c.reindex(rows["date"]).round(2).values
        filled += len(rows)
    write_table(live, P.forecast, "live", "issue_date", ["issue_date", "station", "date"])
    log(f"korekta prognozy na jutro: uzupełniono {filled} wierszy")
    return live


def gate(st: pd.DataFrame, obs: pd.DataFrame, live: pd.DataFrame, today: dt.date) -> Dict:
    """Bramka jakości danych przed publikacją."""
    ok_obs = obs[(obs["stuck"] == 0) & obs["pm25"].notna()]
    last = ok_obs.groupby("station")["date"].max()
    limit = pd.Timestamp(today) - pd.Timedelta(days=config.FRESH_DAYS)
    fresh = int((last >= limit).sum())
    share = fresh / max(1, len(st))
    today_fc = live[live["issue_date"] == pd.Timestamp(today)]["station"].nunique()
    problems = []
    if share < config.GATE_MIN_FRESH_SHARE:
        problems.append(f"świeży pomiar ma tylko {fresh} z {len(st)} stacji")
    if today_fc < 0.9 * len(st):
        problems.append(f"dzisiejsza prognoza jest tylko dla {today_fc} z {len(st)} stacji")
    return {"passed": not problems, "fresh_stations": fresh, "stations": int(len(st)),
            "forecast_stations": int(today_fc), "problems": problems}


# ---------------------------------------------------------------- miary

def _win(x: pd.DataFrame, today: dt.date, days: int) -> pd.DataFrame:
    return x[x.index > pd.Timestamp(today) - pd.Timedelta(days=days + 1)]


def _hypotheses(per_station: Dict[str, pd.DataFrame], today: dt.date) -> Dict:
    """Test potwierdzający (protokół A1) na oknie dni docelowych zapisanym przed startem."""
    a = pd.Timestamp(config.LIVE_TEST_START)
    b = a + pd.Timedelta(days=config.LIVE_TEST_DAYS - 1)
    done = pd.Timestamp(today) > b + pd.Timedelta(days=7)        # tydzień zapasu na spóźnione pomiary
    better = counted = 0
    csi_better = csi_counted = 0
    for x in per_station.values():
        w = x[(x.index >= a) & (x.index <= b)]
        if len(w) < config.MIN_PAIRS:
            continue
        s = core.scores(w, config.THRESHOLD)
        counted += 1
        better += int(s["rmse_fc"] < s["rmse_pers"])
        if s["exceed_days"] >= config.MIN_EXCEEDANCES and s["csi_fc"] is not None and s["csi_pers"] is not None:
            csi_counted += 1
            csi_better += int(s["csi_fc"] > s["csi_pers"])
    elapsed = int(min(config.LIVE_TEST_DAYS, max(0, (pd.Timestamp(today) - a).days)))
    lo, hi = core.wilson(better, counted)
    h1 = {"stations": counted, "better": better, "share": round(better / counted, 3) if counted else None,
          "ci": [lo, hi], "needed": round(2 / 3, 3)}
    h2 = {"stations": csi_counted, "better": csi_better, "needed": "more than half, at least 5 stations"}
    if not done:
        h1["status"] = h2["status"] = "in progress"
    else:
        h1["status"] = "not testable" if counted == 0 else ("confirmed" if better / counted >= 2 / 3 else "not confirmed")
        h2["status"] = ("not testable" if csi_counted < 5 else
                        ("confirmed" if csi_better / csi_counted > 0.5 else "not confirmed"))
    return {"window": [a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")], "days_elapsed": elapsed,
            "days_total": config.LIVE_TEST_DAYS, "final": bool(done), "H-A1": h1, "H-A2": h2}


def _share_status(k: int, n: int, final: bool = True) -> str:
    if not final:
        return "in progress"
    return "not testable" if n == 0 else ("confirmed" if k / n >= 2 / 3 else "not confirmed")


def _hypotheses_a2(corr: Dict[str, pd.DataFrame], raw: Dict[str, pd.DataFrame], today: dt.date) -> Dict:
    """Test na żywo protokołu A2: skorygowana prognoza na jutro wobec reguły (H-A3) i wobec prognozy surowej (H-A4)."""
    a = pd.Timestamp(config.LIVE_TEST_A2_START)
    b = a + pd.Timedelta(days=config.LIVE_TEST_DAYS - 1)
    done = pd.Timestamp(today) > b + pd.Timedelta(days=7)
    n = k3 = k4 = 0
    for sid, x in corr.items():
        w = x[(x.index >= a) & (x.index <= b)]
        r = raw.get(sid, x.iloc[0:0])
        r = r[(r.index >= a) & (r.index <= b)]
        if len(w) < config.MIN_PAIRS or len(r) < config.MIN_PAIRS:
            continue
        sc, sr = core.scores(w, config.THRESHOLD), core.scores(r, config.THRESHOLD)
        n += 1
        k3 += int(sc["rmse_fc"] < sc["rmse_pers"])
        k4 += int(sc["rmse_fc"] < sr["rmse_fc"])
    return {"window": [a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")],
            "days_elapsed": int(min(config.LIVE_TEST_DAYS, max(0, (pd.Timestamp(today) - a).days))),
            "days_total": config.LIVE_TEST_DAYS, "final": bool(done),
            "H-A3": {"stations": n, "better": k3, "status": _share_status(k3, n, done)},
            "H-A4": {"stations": n, "better": k4, "status": _share_status(k4, n, done)}}


def evaluate(st: pd.DataFrame, obs: pd.DataFrame, arch: pd.DataFrame, live: pd.DataFrame, today: dt.date,
             gate_info: Dict) -> Dict:
    """Wynik do publikacji: miary dla każdej stacji, podsumowanie, stan testu potwierdzającego."""
    good = obs[(obs["stuck"] == 0) & obs["pm25"].notna()]
    o_all = good.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    f_arch = arch.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    l1 = live[live["lead"] == 1].pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    if "pm25_corr" not in live:
        live = live.assign(pm25_corr=float("nan"))
    l1c = live[(live["lead"] == 1) & live["pm25_corr"].notna()].pivot_table(index="date", columns="station",
                                                                             values="pm25_corr", aggfunc="first")
    h0, h1 = pd.Timestamp(config.HOLDOUT[0]), pd.Timestamp(config.HOLDOUT[1])
    live_corr_pairs: Dict[str, pd.DataFrame] = {}
    last_issue = live["issue_date"].max()
    latest = live[live["issue_date"] == last_issue]
    stuck = obs[obs["stuck"] == 1].groupby("station").size()
    stations, live_pairs = [], {}
    yesterday = pd.Timestamp(today) - pd.Timedelta(days=1)
    for _, s in st.iterrows():
        sid = s["id"]
        o = o_all[sid].dropna() if sid in o_all else pd.Series(dtype=float)
        xa = core.paired(o, f_arch[sid]) if sid in f_arch else core.paired(o, pd.Series(dtype=float))
        xl = core.paired(o, l1[sid]) if sid in l1 else core.paired(o, pd.Series(dtype=float))
        live_pairs[sid] = xl
        x365 = _win(xa, today, 365)
        s365 = core.scores(x365, config.THRESHOLD)
        lo, hi = core.skill_ci(x365, config.BOOT_BLOCK, config.BOOT_REPS, config.BOOT_SEED)
        sl = core.scores(xl, config.THRESHOLD)
        llo, lhi = core.skill_ci(xl, config.BOOT_BLOCK, config.BOOT_REPS, config.BOOT_SEED)
        winter = xa[xa.index.month.isin([11, 12, 1, 2, 3])]
        # prognoza skorygowana (protokół A2): regresja MOS, współczynniki tylko z dni wcześniejszych
        if sid in f_arch and len(o):
            idx_all = pd.date_range(f_arch.index.min(), yesterday)
            c_arch = correct.mos(o.reindex(idx_all), f_arch[sid].reindex(idx_all), lag=1, window=config.MOS_WINDOW)
        else:
            c_arch = pd.Series(dtype=float)
        xc = core.paired(o, c_arch)
        xc365 = _win(xc, today, 365)
        c365 = core.scores(xc365, config.THRESHOLD)
        clo, chi = core.skill_ci(xc365, config.BOOT_BLOCK, config.BOOT_REPS, config.BOOT_SEED)
        raw_h = core.scores(xa[(xa.index >= h0) & (xa.index <= h1)], config.THRESHOLD)
        cor_h = core.scores(xc[(xc.index >= h0) & (xc.index <= h1)], config.THRESHOLD)
        xlc = core.paired(o, l1c[sid]) if sid in l1c else core.paired(o, pd.Series(dtype=float))
        live_corr_pairs[sid] = xlc
        years = []
        for y in range(pd.Timestamp(config.START).year, today.year + 1):
            oy = o[o.index.year == y]
            years.append({"year": y, "days": int(len(oy)), "exceed": int((oy > config.THRESHOLD).sum())})
        idx = pd.date_range(yesterday - pd.Timedelta(days=config.CHART_DAYS - 1), yesterday)
        chart = {"dates": [d.strftime("%Y-%m-%d") for d in idx],
                 "obs": _vals(o.reindex(idx)),
                 "fc": _vals(f_arch[sid].reindex(idx)) if sid in f_arch else [None] * len(idx),
                 "fc_live": _vals(l1[sid].reindex(idx)) if sid in l1 else [None] * len(idx),
                 "fc_corr": _vals(c_arch.reindex(idx)) if len(c_arch) else [None] * len(idx)}
        nxt = latest[latest["station"] == sid].set_index("lead")["pm25"]
        nxc = latest[latest["station"] == sid].set_index("lead")["pm25_corr"]
        last30 = o[(o.index > yesterday - pd.Timedelta(days=30)) & (o.index <= yesterday)]
        stations.append({
            "id": sid, "country": s["country"], "city": s["city"], "name": s["name"], "lat": float(s["lat"]),
            "lon": float(s["lon"]),
            "forecast": {"issued": last_issue.strftime("%Y-%m-%d") if pd.notna(last_issue) else None,
                         "today": _num(nxt.get(0)), "tomorrow": _num(nxt.get(1)), "day2": _num(nxt.get(2)),
                         "tomorrow_corrected": _num(nxc.get(1))},
            "corrected_365": {**c365, "skill_ci": [clo, chi], "verdict": core.verdict(c365, clo, chi, config.MIN_PAIRS)},
            "holdout": {"raw": raw_h, "corrected": cor_h},
            "live_corrected": core.scores(xlc, config.THRESHOLD),
            "archive_365": {**s365, "skill_ci": [lo, hi], "verdict": core.verdict(s365, lo, hi, config.MIN_PAIRS)},
            "archive_30": core.scores(_win(xa, today, 30), config.THRESHOLD),
            "archive_all": core.scores(xa, config.THRESHOLD),
            "archive_winter": core.scores(winter, config.THRESHOLD),
            "live": {**sl, "skill_ci": [llo, lhi], "verdict": core.verdict(sl, llo, lhi, config.MIN_PAIRS)},
            "years": years, "chart": chart,
            "latest_obs": {"date": o.index.max().strftime("%Y-%m-%d") if len(o) else None,
                           "pm25": _num(o.iloc[-1]) if len(o) else None},
            "qc": {"last_obs": o.index.max().strftime("%Y-%m-%d") if len(o) else None,
                   "missing_last30": int(30 - len(last30)), "stuck_days": int(stuck.get(sid, 0))},
        })
    verdicts = [s["archive_365"]["verdict"] for s in stations]
    cverd = [s["corrected_365"]["verdict"] for s in stations]
    hs = [s["holdout"] for s in stations if s["holdout"]["raw"].get("n", 0) >= config.MIN_PAIRS
          and s["holdout"]["corrected"].get("n", 0) >= config.MIN_PAIRS]
    k_cp = sum(h["corrected"]["rmse_fc"] < h["corrected"]["rmse_pers"] for h in hs)
    k_cr = sum(h["corrected"]["rmse_fc"] < h["raw"]["rmse_fc"] for h in hs)
    k_rp = sum(h["raw"]["rmse_fc"] < h["raw"]["rmse_pers"] for h in hs)

    def med(key: str, part: str) -> Optional[float]:
        return round(float(pd.Series([h[part][key] for h in hs]).median()), 3) if hs else None

    holdout = {"period": list(config.HOLDOUT), "stations": len(hs),
               "raw_beats_persistence": int(k_rp), "corrected_beats_persistence": int(k_cp),
               "corrected_beats_raw": int(k_cr), "median_skill_raw": med("skill", "raw"),
               "median_skill_corrected": med("skill", "corrected"), "median_rmse_raw": med("rmse_fc", "raw"),
               "median_rmse_corrected": med("rmse_fc", "corrected"), "median_rmse_persistence": med("rmse_pers", "raw"),
               "H-A3": _share_status(int(k_cp), len(hs)), "H-A4": _share_status(int(k_cr), len(hs))}
    summary = {
        "stations": len(stations), "countries": sorted({s["country"] for s in stations}),
        "archive_365": {v: verdicts.count(v) for v in ("better", "similar", "worse", "insufficient")},
        "corrected_365": {v: cverd.count(v) for v in ("better", "similar", "worse", "insufficient")},
        "holdout": holdout,
        "live_pairs_max": int(max([len(x) for x in live_pairs.values()] or [0])),
        "first_issue": live["issue_date"].min().strftime("%Y-%m-%d") if len(live) else None,
        "model_run": str(latest["model_run"].iloc[0]) if len(latest) else "",
    }
    return {"project": "air-check", "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "run_date": today.isoformat(), "threshold": config.THRESHOLD, "gate": gate_info, "summary": summary,
            "test": _hypotheses(live_pairs, today), "test_a2": _hypotheses_a2(live_corr_pairs, live_pairs, today),
            "stations": stations}


def _num(v) -> Optional[float]:
    return None if v is None or pd.isna(v) else round(float(v), 1)


def _vals(s: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 1) for v in s.values]


# ---------------------------------------------------------------- przebieg

def run(root: str | Path | None = None, today: dt.date | None = None, backfill: bool = False,
        sources: Sources | None = None, stations: pd.DataFrame | None = None, log: Callable = print) -> int:
    """Jeden przebieg. Zwraca 0 (opublikowano), 2 (bramka jakości zatrzymała publikację) albo 1 (błąd)."""
    P = config.paths(root)
    today = today or dt.datetime.now(dt.timezone.utc).date()
    src = sources or Sources()
    status = {"project": "air-check", "run_date": today.isoformat(), "backfill": bool(backfill),
              "started": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    code = 1
    try:
        st = stations if stations is not None else registry.load()
        log(f"Air Check {today}: stacji {len(st)}, rekonstrukcja: {backfill}")
        obs = update_obs(st, P, src, backfill, log, today)
        # Najpierw prognoza wydana dziś: tylko jej nie da się odtworzyć później.
        live = update_live(st, P, src, today, log)
        try:
            arch = update_archive(st, P, src, today, backfill, log)
        except Exception as e:
            # Archiwum samo się uzupełni przy następnym przebiegu (pobieramy zawsze ostatnie 10 dni).
            arch = read_table(P.forecast, "archive", ["date"])
            if backfill or arch.empty:
                raise
            status["warnings"] = [f"archiwum prognoz nieodświeżone: {e}"]
            log(f"uwaga: archiwum prognoz nieodświeżone ({e}); używam zapisanego, do {arch['date'].max().date()}")
        try:
            live = add_live_correction(st, P, obs, arch, live, log)
        except Exception as e:                               # brak korekty nie zatrzymuje przebiegu
            status.setdefault("warnings", []).append(f"korekta prognozy nie policzona: {e}")
            log(f"uwaga: korekta prognozy nie policzona ({e})")
        g = gate(st, obs, live, today)
        status["gate"] = g
        if not g["passed"]:
            log("bramka jakości: NIE przeszła: " + "; ".join(g["problems"]) + " (panel bez zmian)")
            status["status"], code = "gate_failed", 2
        else:
            result = evaluate(st, obs, arch, live, today, g)
            publish.write_all(P, result)
            status["status"], code = "ok", 0
            log(f"opublikowano: {P.showcase}")
    except Exception as e:
        status["status"], status["error"] = "error", f"{type(e).__name__}: {e}"
        log(traceback.format_exc())
    status["finished"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (P.logs / "last_run.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    return code


def render(root: str | Path | None = None, today: dt.date | None = None, stations: pd.DataFrame | None = None,
           log: Callable = print) -> int:
    """Przelicza miary i panel z tabel zapisanych w data/ (bez sieci). Po zmianie kodu panelu albo miar."""
    P = config.paths(root)
    st = stations if stations is not None else registry.load()
    obs = read_table(P.obs, "obs", ["date"])
    arch = read_table(P.forecast, "archive", ["date"])
    live = read_table(P.forecast, "live", ["issue_date", "date"])
    if obs.empty or arch.empty or live.empty:
        log("brak tabel w data/: najpierw `python -m aircheck backfill`")
        return 1
    today = today or live["issue_date"].max().date()
    live = add_live_correction(st, P, obs, arch, live, log)
    publish.write_all(P, evaluate(st, obs, arch, live, today, gate(st, obs, live, today)))
    log(f"panel przeliczony na dzień {today}: {P.showcase}")
    return 0
