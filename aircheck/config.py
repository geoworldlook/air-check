"""Ustawienia Air Check w jednym miejscu. Wartości metod pochodzą z protokołu (zmiana = nowa wersja protokołu)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

START = "2022-01-01"            # początek rekonstrukcji pomiarów (D-097)
ARCHIVE_START = "2023-11-01"    # początek archiwum prognoz u dostawcy
THRESHOLD = 25.0                # µg/m³: doba z wysokim pyłem (średnia dobowa PM2.5)
MIN_PAIRS = 60                  # najmniej par dni, żeby liczyć stację w teście
MIN_EXCEEDANCES = 10            # najmniej dni powyżej progu, żeby liczyć stację w H-A2
LIVE_TEST_START = "2026-11-16"  # pierwszy dzień docelowy testu potwierdzającego (protokół A1)
LIVE_TEST_DAYS = 90
GATE_MIN_FRESH_SHARE = 0.5      # bramka jakości: udział stacji ze świeżym pomiarem
FRESH_DAYS = 4                  # świeży = pomiar z ostatnich 4 dni
BOOT_BLOCK, BOOT_REPS, BOOT_SEED = 7, 400, 20261114
CHART_DAYS = 120

PROTOCOL = Path("docs") / "evidence" / "A1_protokol_prognozy.md"
PROTOCOL_SHA256 = "8e2999e3ad8fac92973575ba5a234f4448dfbab378c05e4dc50ccd4bf3fee268"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def obs(self) -> Path:
        return self.root / "data" / "obs"

    @property
    def forecast(self) -> Path:
        return self.root / "data" / "forecast"

    @property
    def logs(self) -> Path:
        return self.root / "data" / "logs"

    @property
    def showcase(self) -> Path:
        return self.root / "docs" / "showcase"

    def ensure(self) -> "Paths":
        for p in (self.obs, self.forecast, self.logs, self.showcase):
            p.mkdir(parents=True, exist_ok=True)
        return self


def paths(root: str | os.PathLike | None = None) -> Paths:
    """Katalog roboczy: argument, zmienna AIRCHECK_ROOT albo katalog repozytorium."""
    return Paths(Path(root or os.environ.get("AIRCHECK_ROOT") or ROOT)).ensure()
