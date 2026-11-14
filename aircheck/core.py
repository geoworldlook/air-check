"""Miary zgodności prognozy z pomiarem i porównanie z regułą „jutro jak dziś”.

Para dni: pomiar w dniu D (o), prognoza na dzień D (f) i pomiar z dnia D-1 (p, czyli reguła „jutro jak dziś”).
Skill = 1 - MSE(prognoza) / MSE(reguła): powyżej zera prognoza jest lepsza od reguły.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


def paired(obs: pd.Series, fc: pd.Series) -> pd.DataFrame:
    """Tabela par (o, f, p) na wspólnych dniach; p to pomiar z poprzedniego dnia kalendarzowego."""
    obs = obs.dropna()
    fc = fc.dropna()
    if obs.empty or fc.empty:
        return pd.DataFrame(columns=["o", "f", "p"])
    prev = pd.Series(obs.values, index=obs.index + pd.Timedelta(days=1))
    x = pd.DataFrame({"o": obs, "f": fc, "p": prev}).dropna()
    x.index.name = "date"
    return x


def _csi(o: np.ndarray, f: np.ndarray, thr: float) -> Tuple[int, int, int, Optional[float]]:
    hits = int(((o > thr) & (f > thr)).sum())
    miss = int(((o > thr) & (f <= thr)).sum())
    false = int(((o <= thr) & (f > thr)).sum())
    tot = hits + miss + false
    return hits, miss, false, (hits / tot if tot else None)


def scores(x: pd.DataFrame, thr: float) -> Dict[str, Optional[float]]:
    """Miary dla tabeli par. Gdy brak danych, zwraca tylko n = 0."""
    n = len(x)
    if n == 0:
        return {"n": 0}
    o, f, p = x["o"].to_numpy(float), x["f"].to_numpy(float), x["p"].to_numpy(float)
    mse_f, mse_p = float(np.mean((f - o) ** 2)), float(np.mean((p - o) ** 2))
    hits, miss, false, csi_f = _csi(o, f, thr)
    _, _, _, csi_p = _csi(o, p, thr)
    r = float(np.corrcoef(o, f)[0, 1]) if n > 2 and np.std(o) > 0 and np.std(f) > 0 else None
    return {
        "n": n, "obs_mean": round(float(o.mean()), 1), "bias": round(float((f - o).mean()), 1),
        "rmse_fc": round(mse_f ** 0.5, 2), "rmse_pers": round(mse_p ** 0.5, 2),
        "skill": round(1 - mse_f / mse_p, 3) if mse_p > 0 else None, "r": round(r, 2) if r is not None else None,
        "exceed_days": int((o > thr).sum()), "hits": hits, "misses": miss, "false_alarms": false,
        "csi_fc": round(csi_f, 2) if csi_f is not None else None,
        "csi_pers": round(csi_p, 2) if csi_p is not None else None,
    }


def skill_ci(x: pd.DataFrame, block: int, reps: int, seed: int) -> Tuple[Optional[float], Optional[float]]:
    """95% przedział ufności dla skill: bootstrap blokowy po dniach (bloki kolejnych dni, losowane ze zwracaniem)."""
    n = len(x)
    if n < 4 * block:
        return None, None
    ef = (x["f"].to_numpy(float) - x["o"].to_numpy(float)) ** 2
    ep = (x["p"].to_numpy(float) - x["o"].to_numpy(float)) ** 2
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    sp = ep[idx].mean(axis=1)
    sk = 1 - ef[idx].mean(axis=1) / np.where(sp > 0, sp, np.nan)
    if np.isnan(sk).all():
        return None, None
    lo, hi = np.nanpercentile(sk, [2.5, 97.5])
    return round(float(lo), 3), round(float(hi), 3)


def verdict(s: Dict[str, Optional[float]], lo: Optional[float], hi: Optional[float], min_pairs: int) -> str:
    """better / worse / similar / insufficient: rozstrzygamy tylko wtedy, gdy przedział ufności nie obejmuje zera."""
    if s.get("n", 0) < min_pairs or s.get("skill") is None or lo is None or hi is None:
        return "insufficient"
    if lo > 0:
        return "better"
    if hi < 0:
        return "worse"
    return "similar"


def wilson(k: int, n: int) -> Tuple[Optional[float], Optional[float]]:
    """95% przedział Wilsona dla udziału k/n."""
    if n == 0:
        return None, None
    z, ph = 1.96, k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)
