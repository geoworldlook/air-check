"""Eksperyment A2: wybór metody korekty prognozy (post-processing) na okresie rozwojowym.

Wszystkie metody są przyczynowe: korekta na dzień D używa tylko pomiarów i prognoz sprzed dnia D.
Okres rozwojowy: dni do 2025-11-15. Okres odłożony (ostatnie 365 dni do 2026-11-15) NIE jest tu liczony;
ocenia go potok po zamrożeniu metody (protokół A2).

Metody z literatury (Bertrand i in. 2023 wymieniają trzy pierwsze jako najczęściej stosowane):
  bias_N     bieżąca korekta addytywna: prognoza minus średni błąd z ostatnich N dni
  ratio_N    bieżąca korekta mnożnikowa: prognoza razy (suma pomiarów / suma prognoz) z ostatnich N dni
  kalman_r   filtr Kalmana dla błędu prognozy (Delle Monache i in. 2006), r = stosunek wariancji
  hybrid     pomiar z wczoraj plus zmiana prognozy z dnia na dzień
  mos_W      regresja MOS: pomiar ~ prognoza + pomiar z wczoraj, dopasowana na ostatnich W dniach

Uruchomienie:  conda run -n aircheck python notebooks/experiments/A2_wybor_korekty.py
Wynik:         docs/evidence/A2_wybor_korekty.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aircheck import config, core, correct, pipeline, registry  # noqa: E402

DEV_END = "2025-11-15"


def main() -> int:
    P = config.paths(ROOT)
    st = registry.load()
    obs = pipeline.read_table(P.obs, "obs", ["date"])
    arch = pipeline.read_table(P.forecast, "archive", ["date"])
    good = obs[(obs["stuck"] == 0) & obs["pm25"].notna()]
    O = good.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    F = arch.pivot_table(index="date", columns="station", values="pm25", aggfunc="first")
    rows = []
    for name, fn in correct.CANDIDATES.items():
        skills, wins, n = [], 0, 0
        for sid in st["id"]:
            if sid not in O or sid not in F:
                continue
            idx = pd.date_range(F.index.min(), pd.Timestamp(DEV_END))
            o, f = O[sid].reindex(idx), F[sid].reindex(idx)
            c = fn(o, f, lag=1)
            x = core.paired(o, c)
            x = x[x.index >= pd.Timestamp("2024-03-01")]          # pierwsze miesiące to rozruch metod z długim oknem
            if len(x) < 200:
                continue
            s = core.scores(x, config.THRESHOLD)
            skills.append(s["skill"])
            wins += int(s["rmse_fc"] < s["rmse_pers"])
            n += 1
        rows.append({"method": name, "stations": n, "wins_vs_persistence": wins,
                     "median_skill": round(float(np.median(skills)), 3), "min_skill": round(float(np.min(skills)), 3),
                     "q25_skill": round(float(np.percentile(skills, 25)), 3)})
        print(rows[-1], flush=True)
    out = pd.DataFrame(rows).sort_values(["wins_vs_persistence", "median_skill"], ascending=False)
    out.to_csv(ROOT / "docs" / "evidence" / "A2_wybor_korekty.csv", index=False, lineterminator="\n")
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
