"""Publikacja wyniku do docs/showcase/: panel (jeden plik HTML z danymi w środku), dane JSON, punkty mapy, stan.

Panel działa bez serwera (dane są wbudowane). Leaflet 1.9.4: skrypt z unpkg, arkusz stylów wbudowany
(aircheck/assets/), tak samo jak w AgriScreen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from . import config

ASSETS = Path(__file__).resolve().parent / "assets"
PANEL_URL = "https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html"
WORDS = {"better": "forecast beats the rule 'tomorrow = today'", "worse": "the rule 'tomorrow = today' beats the forecast",
         "similar": "forecast and the rule 'tomorrow = today' are about equal", "insufficient": "too few days for a verdict"}


def panel_html(result: Dict) -> str:
    tpl = (ASSETS / "panel_template.html").read_text(encoding="utf-8")
    css = (ASSETS / "leaflet-1.9.4.css").read_text(encoding="utf-8") if (ASSETS / "leaflet-1.9.4.css").exists() else ""
    data = json.dumps(result, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return tpl.replace("/*LEAFLET_CSS*/", css).replace("/*DATA*/", data)


def map_points(result: Dict) -> Dict:
    """Punkty dla mapy monitorowania na stronie (GeoJSON; title i description trafiają do dymka)."""
    feats = []
    for s in result["stations"]:
        a = s["archive_365"]
        tom = s["forecast"]["tomorrow"]
        last = s.get("latest_obs") or {}
        corr = s["forecast"].get("tomorrow_corrected")
        hr, hc = s["holdout"]["raw"], s["holdout"]["corrected"]
        desc = (f"Measured at the station on {last['date']}: {last['pm25']} µg/m³ PM2.5. " if last.get("pm25") is not None else "")
        if corr is not None:
            desc += f"Corrected forecast for tomorrow: {corr} µg/m³ (raw Copernicus forecast: {tom if tom is not None else 'n/a'}). "
        else:
            desc += f"Forecast for tomorrow: {tom if tom is not None else 'n/a'} µg/m³. "
        if hc.get("n"):
            desc += (f"Typical error in the hold-out year: corrected {hc['rmse_fc']}, raw {hr['rmse_fc']}, "
                     f"rule 'tomorrow = today' {hc['rmse_pers']} µg/m³.")
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                      "properties": {"project": "air-check", "id": s["id"], "title": f"Air Check · {s['city']}",
                                     "description": desc, "status": s["corrected_365"]["verdict"],
                                     "raw_status": a["verdict"], "updated": result["run_date"],
                                     "reading": last.get("pm25"), "reading_unit": "µg/m³ PM2.5",
                                     "reading_date": last.get("date"), "forecast_tomorrow": tom,
                                     "forecast_tomorrow_corrected": corr, "url": PANEL_URL}})
    return {"type": "FeatureCollection", "features": feats}


def status(result: Dict) -> Dict:
    return {"project": "air-check", "updated": result["updated"], "run_date": result["run_date"],
            "gate": result["gate"], "summary": result["summary"], "test": result["test"],
            "test_a2": result["test_a2"]}


def write_all(P: config.Paths, result: Dict) -> None:
    P.showcase.mkdir(parents=True, exist_ok=True)

    def dump(name: str, obj: Dict, indent=None) -> None:
        (P.showcase / name).write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")

    dump("aircheck_data.json", result)
    dump("map_points.geojson", map_points(result), indent=1)
    dump("status.json", status(result), indent=1)
    (P.showcase / "aircheck_panel.html").write_text(panel_html(result), encoding="utf-8")
