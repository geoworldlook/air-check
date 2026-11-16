"""Korekta prognozy (post-processing): proste metody z literatury, wszystkie przyczynowe.

Korekta na dzień D używa wyłącznie tego, co było znane przed dniem D:
  - prognozy na dzień D (i wcześniejszych prognoz),
  - pomiarów do dnia D - lag (lag = 1 dla prognoz z archiwum, lag = 2 dla prognozy na jutro wydanej rano:
    wczorajsza doba nie jest wtedy jeszcze pełna).

Źródła metod: bieżąca korekta błędu i filtr Kalmana (Delle Monache i in. 2006; Kang i in. 2008),
regresja MOS z pomiarem z poprzedniego dnia (przegląd: Bertrand i in. 2023, Atmos. Chem. Phys. 23, 5317).
Wejście: dwa szeregi dobowe na tym samym, ciągłym kalendarzu (braki jako NaN). Wyjście: szereg skorygowany.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np
import pandas as pd

MIN_TRAIN = 30          # najmniej par dni, żeby dopasować korektę; wcześniej zwracamy prognozę surową


def _known(obs: pd.Series, fc: pd.Series, lag: int):
    """Pary (pomiar, prognoza) przesunięte tak, że w wierszu D leży ostatnia para znana przed dniem D."""
    return obs.shift(lag), fc.shift(lag)


def bias(obs: pd.Series, fc: pd.Series, lag: int = 1, window: int = 14) -> pd.Series:
    """Bieżąca korekta addytywna: prognoza minus średni błąd z ostatnich `window` znanych dni."""
    o, f = _known(obs, fc, lag)
    err = (f - o).rolling(window, min_periods=max(3, window // 3)).mean()
    return (fc - err).where(err.notna(), fc).clip(lower=0)


def ratio(obs: pd.Series, fc: pd.Series, lag: int = 1, window: int = 14) -> pd.Series:
    """Bieżąca korekta mnożnikowa: prognoza razy (suma pomiarów / suma prognoz) z ostatnich `window` znanych dni."""
    o, f = _known(obs, fc, lag)
    both = o.notna() & f.notna()
    so = o.where(both).rolling(window, min_periods=max(3, window // 3)).sum()
    sf = f.where(both).rolling(window, min_periods=max(3, window // 3)).sum()
    k = (so / sf).clip(0.2, 5.0)
    return (fc * k).where(k.notna(), fc)


def kalman(obs: pd.Series, fc: pd.Series, lag: int = 1, r: float = 0.06) -> pd.Series:
    """Filtr Kalmana dla błędu prognozy (Delle Monache i in. 2006). r to stosunek wariancji szumu procesu do pomiaru:
    większe r = szybsza reakcja na zmianę błędu. Błąd szacujemy rekurencyjnie z kolejnych znanych dni."""
    o, f = _known(obs, fc, lag)
    err = (f - o).to_numpy(float)
    est = np.full(len(err), np.nan)
    x, p = 0.0, 1.0
    seen = 0
    for i, e in enumerate(err):
        if np.isfinite(e):
            p = p + r
            k = p / (p + 1.0)
            x = x + k * (e - x)
            p = (1.0 - k) * p
            seen += 1
        if seen >= 3:
            est[i] = x
    est = pd.Series(est, index=fc.index)
    return (fc - est).where(est.notna(), fc).clip(lower=0)


def hybrid(obs: pd.Series, fc: pd.Series, lag: int = 1) -> pd.Series:
    """Pomiar z ostatniego znanego dnia plus zmiana prognozy między tym dniem a dniem D."""
    o, f = _known(obs, fc, lag)
    c = o + (fc - f)
    return c.where(c.notna(), fc).clip(lower=0)


def mos(obs: pd.Series, fc: pd.Series, lag: int = 1, window: int = 120) -> pd.Series:
    """Regresja MOS: pomiar(D) ~ a + b * prognoza(D) + c * pomiar(D - lag), dopasowana metodą najmniejszych kwadratów
    na ostatnich `window` dniach z kompletem. Współczynniki dla dnia D pochodzą tylko z dni wcześniejszych."""
    prev = obs.shift(lag)
    y, x1, x2 = obs.to_numpy(float), fc.to_numpy(float), prev.to_numpy(float)
    out = fc.to_numpy(float).copy()
    ok = np.isfinite(y) & np.isfinite(x1) & np.isfinite(x2)
    for i in range(len(y)):
        if not (np.isfinite(x1[i]) and np.isfinite(x2[i])):
            continue
        hi = i - lag + 1                        # do dopasowania wchodzą dni, których pomiar jest już znany
        lo = max(0, hi - window)
        m = ok[lo:hi]
        if m.sum() < MIN_TRAIN:
            continue
        A = np.column_stack([np.ones(int(m.sum())), x1[lo:hi][m], x2[lo:hi][m]])
        coef, *_ = np.linalg.lstsq(A, y[lo:hi][m], rcond=None)
        out[i] = coef[0] + coef[1] * x1[i] + coef[2] * x2[i]
    return pd.Series(out, index=fc.index).clip(lower=0)


CANDIDATES: Dict[str, Callable] = {
    "bias_7": lambda o, f, lag=1: bias(o, f, lag, 7),
    "bias_14": lambda o, f, lag=1: bias(o, f, lag, 14),
    "bias_30": lambda o, f, lag=1: bias(o, f, lag, 30),
    "ratio_14": lambda o, f, lag=1: ratio(o, f, lag, 14),
    "ratio_30": lambda o, f, lag=1: ratio(o, f, lag, 30),
    "kalman_0.03": lambda o, f, lag=1: kalman(o, f, lag, 0.03),
    "kalman_0.06": lambda o, f, lag=1: kalman(o, f, lag, 0.06),
    "kalman_0.15": lambda o, f, lag=1: kalman(o, f, lag, 0.15),
    "hybrid": lambda o, f, lag=1: hybrid(o, f, lag),
    "mos_60": lambda o, f, lag=1: mos(o, f, lag, 60),
    "mos_120": lambda o, f, lag=1: mos(o, f, lag, 120),
    "mos_365": lambda o, f, lag=1: mos(o, f, lag, 365),
}
