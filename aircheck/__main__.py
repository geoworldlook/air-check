"""
Polecenia Air Check:

    python -m aircheck run        [--root DIR] [--date RRRR-MM-DD]   przebieg dzienny: pomiary, prognoza, panel
    python -m aircheck backfill   [--root DIR]                       rekonstrukcja od 2022 (raz; kilka minut, sieć)
    python -m aircheck render     [--root DIR]                       panel z zapisanych tabel (bez sieci)
    python -m aircheck publish    [--message TEKST] [--no-push]      commit i push data/ oraz docs/showcase/
    python -m aircheck selftest                                      testy bez sieci (tak samo w CI)
    python -m aircheck settings                                      ustawienia i stan ostatniego przebiegu
    python -m aircheck stations   [--write]                          propozycja rejestru stacji z metadanych EEA

Kody wyjścia `run`: 0 = opublikowano, 2 = bramka jakości zatrzymała publikację, 1 = błąd.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

from . import __version__, config


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(config.ROOT), *args], capture_output=True, text=True, encoding="utf-8")


def publish(message: str | None, push: bool) -> int:
    """Commit zmian w data/ i docs/showcase/ (autor z ustawień repozytorium) i wypchnięcie na GitHub."""
    _git("add", "data", "docs/showcase")
    if not _git("diff", "--cached", "--name-only").stdout.strip():
        print("publish: brak zmian")
        return 0
    msg = message or f"auto: przebieg dzienny {dt.datetime.now(dt.timezone.utc).date()}"
    c = _git("commit", "-m", msg)
    if c.returncode:
        print(c.stdout, c.stderr)
        return 1
    print(f"publish: commit „{msg}”")
    if push:
        p = _git("push")
        print((p.stdout + p.stderr).strip())
        return p.returncode
    return 0


def settings() -> int:
    P = config.paths()
    info = {"version": __version__, "root": str(P.root), "start": config.START, "archive_start": config.ARCHIVE_START,
            "threshold_ug_m3": config.THRESHOLD, "live_test": [config.LIVE_TEST_START, config.LIVE_TEST_DAYS],
            "protocol": str(config.PROTOCOL), "protocol_sha256": config.PROTOCOL_SHA256}
    last = P.logs / "last_run.json"
    if last.exists():
        info["last_run"] = json.loads(last.read_text(encoding="utf-8"))
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m aircheck", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "backfill", "render"):
        p = sub.add_parser(name)
        p.add_argument("--root")
        p.add_argument("--date")
    p = sub.add_parser("publish")
    p.add_argument("--message")
    p.add_argument("--no-push", action="store_true")
    sub.add_parser("selftest")
    sub.add_parser("settings")
    p = sub.add_parser("stations")
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd in ("run", "backfill", "render"):
        from . import pipeline
        day = dt.date.fromisoformat(a.date) if a.date else None
        if a.cmd == "render":
            return pipeline.render(a.root, day)
        return pipeline.run(a.root, day, backfill=(a.cmd == "backfill"))
    if a.cmd == "publish":
        return publish(a.message, not a.no_push)
    if a.cmd == "selftest":
        from . import selftest
        return selftest.main()
    if a.cmd == "settings":
        return settings()
    if a.cmd == "stations":
        from . import registry
        d = registry.build()
        print(d["status"].value_counts().to_dict())
        print(d.loc[d["status"] == "excluded", ["country", "city", "reason"]].to_string(index=False))
        if a.write:                                         # rejestr zawiera tylko stacje przyjęte
            keep = d[d["status"] == "accepted"].drop(columns=["reason"])
            keep.to_csv(registry.STATIONS_CSV, index=False, encoding="utf-8", lineterminator="\n")
            print(f"zapisano {registry.STATIONS_CSV} ({len(keep)} stacji)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
