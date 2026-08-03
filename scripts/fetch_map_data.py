"""Pobiera dane map trasy Deepnight Revelation do companion/data/sectors/.

Zrodla:
  1. Repo travellermap (GitHub): res/Sectors/DeepnightRevelation/ - milieu XML
     + pliki dotmap (sektory Wielkiej Szczeliny, autorzy Lanesskog/Dougherty).
  2. API travellermap.com: /data/{sector}/tab + /api/metadata dla sektorow
     Charted Space z etapu 1 trasy (Vland, Harea).

Wyjscie:
  companion/data/sectors/raw/       - pliki zrodlowe 1:1
  companion/data/sectors/sectors.json - znormalizowany model dla serwera
  companion/data/sectors/manifest.json - atrybucja, URL-e, data pobrania

Uzycie: py -3.12 scripts/fetch_map_data.py [--skip-existing]
Licencja danych: travellermap.com - personal, non-commercial use only.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "companion" / "data" / "sectors"
RAW_DIR = OUT_DIR / "raw"

GH_BASE = (
    "https://raw.githubusercontent.com/inexorabletash/travellermap/master"
    "/res/Sectors/DeepnightRevelation"
)
TM_BASE = "https://travellermap.com"

# Sektory Charted Space potrzebne dla etapu 1 (Giikur -> Demnan).
# Reszta etapu 1 jest abstrahowana (Rate of Advance), wiec nie ciagniemy
# wszystkich 9 sektorow korytarza.
CHARTED_SECTORS = ["Vland", "Harea"]

UNSURVEYED_UWP = "???????-?"


def fetch(url: str, dest: Path, skip_existing: bool) -> bytes:
    if skip_existing and dest.exists():
        return dest.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "deepnight-companion/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    time.sleep(0.5)  # nie mlocic serwera
    return data


def parse_milieu_xml(xml_bytes: bytes) -> list[dict]:
    """DeepnightRevelation.xml -> lista sektorow z X/Y, nazwa, DataFile, atrybucja."""
    root = ET.fromstring(xml_bytes)
    sectors = []
    for sec in root.iter("Sector"):
        name_el = sec.find("Name")
        datafile_el = sec.find("DataFile")
        if name_el is None:
            continue
        sectors.append(
            {
                "name": (name_el.text or "").strip(),
                "x": int(sec.findtext("X", "0")),
                "y": int(sec.findtext("Y", "0")),
                "author": name_el.get("Author") or (datafile_el.get("Author") if datafile_el is not None else None),
                "source": name_el.get("Source"),
                "datafile": datafile_el.text.strip() if datafile_el is not None and datafile_el.text else None,
            }
        )
    return sectors


def parse_fixed_width(text: str) -> list[dict]:
    """Parsuje format T5 fixed-width (dotmapy): naglowek + linia myslnikow.

    Szerokosci kolumn wyznacza linia myslnikow (grupy '-' oddzielone spacjami).
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("Hex") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= {"-", " "}:
            header_idx = i
            break
    if header_idx is None:
        return []
    header, ruler = lines[header_idx], lines[header_idx + 1]
    # kolumny = zakresy grup myslnikow
    cols = []
    start = None
    for pos, ch in enumerate(ruler):
        if ch == "-" and start is None:
            start = pos
        elif ch != "-" and start is not None:
            cols.append((start, pos))
            start = None
    if start is not None:
        cols.append((start, len(ruler)))
    names = [header[s:e].strip() for s, e in cols]
    rows = []
    for ln in lines[header_idx + 2:]:
        row = {}
        for (s, e), name in zip(cols, names):
            row[name] = ln[s:e].strip() if s < len(ln) else ""
        # ostatnia kolumna moze wystawac poza ruler
        if cols:
            last_s = cols[-1][0]
            row[names[-1]] = ln[last_s:].strip() if last_s < len(ln) else ""
        rows.append(row)
    return rows


def parse_tab(text: str) -> list[dict]:
    """Parsuje format tab-delimited z /data/{sector}/tab."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, ln.split("\t"))) for ln in lines[1:]]


def normalize_worlds(rows: list[dict]) -> dict[str, dict]:
    """Wspolny model: hex -> {name, uwp, known, stellar, zone, bases, remarks}."""
    worlds = {}
    for r in rows:
        hex_ = r.get("Hex", "")
        if not hex_ or len(hex_) != 4 or not hex_.isdigit():
            continue
        uwp = r.get("UWP", "")
        pbg = r.get("PBG", "")
        gg = None
        if len(pbg) == 3 and pbg[2].isdigit():
            gg = int(pbg[2])  # trzecia cyfra PBG = liczba gazowych olbrzymow
        worlds[hex_] = {
            "name": r.get("Name", ""),
            "uwp": uwp,
            "known": bool(uwp) and uwp != UNSURVEYED_UWP,
            "stellar": r.get("Stellar", r.get("Stars", "")),
            "zone": r.get("Zone", r.get("Z", "")),
            "bases": r.get("Bases", r.get("B", "")),
            "remarks": r.get("Remarks", ""),
            "gg": gg,
        }
    return worlds


def main() -> int:
    skip_existing = "--skip-existing" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched": date.today().isoformat(),
        "license": "travellermap.com data: personal, non-commercial use only (FFE Fair Use Policy)",
        "sources": [],
    }
    sectors_out = {}

    # 1. Milieu Deepnight Revelation z repo GitHub
    xml_url = f"{GH_BASE}/DeepnightRevelation.xml"
    print(f"[1/3] {xml_url}")
    xml_bytes = fetch(xml_url, RAW_DIR / "DeepnightRevelation.xml", skip_existing)
    dnr_sectors = parse_milieu_xml(xml_bytes)
    manifest["sources"].append({"url": xml_url, "sectors": len(dnr_sectors)})
    print(f"      sektorow w milieu: {len(dnr_sectors)}")

    # 2. Dotmapy per sektor
    print("[2/3] dotmapy DNR")
    missing = []
    for sec in dnr_sectors:
        rows: list[dict] = []
        no_dotmap = True
        if sec["datafile"]:
            url = f"{GH_BASE}/{urllib.parse.quote(sec['datafile'])}"
            try:
                data = fetch(url, RAW_DIR / sec["datafile"], skip_existing)
                rows = parse_fixed_width(data.decode("utf-8", errors="replace"))
                no_dotmap = False
            except Exception as exc:  # noqa: BLE001 - raport i dalej
                print(f"      BLAD {sec['name']}: {exc}")
        if no_dotmap:
            # Sektor bez opublikowanej dotmapy (FSN/Voidshore): tylko nazwa+koordynaty.
            # Obecnosc gwiazd wygeneruje silnik (B3 p.20 Star System Presence, Rift 2/2D).
            missing.append(sec["name"])
        # sektory "Unnamed" (Uncharted Gap) rozrozniamy koordynatami
        key = sec["name"] if sec["name"] != "Unnamed" else f"Unnamed {sec['x']},{sec['y']}"
        sectors_out[key] = {
            "name": key,
            "x": sec["x"],
            "y": sec["y"],
            "milieu": "DeepnightRevelation",
            "data_status": "Unreviewed/OTU",
            "author": sec["author"],
            "source": sec["source"],
            "worlds_source": "generate" if no_dotmap else "dotmap",
            "worlds": normalize_worlds(rows),
        }
        tag = "GENERATE" if no_dotmap else f"wpisow: {len(sectors_out[key]['worlds'])}"
        print(f"      {key:<28} ({sec['x']:>3},{sec['y']:>3})  {tag}")

    # 3. Sektory Charted Space przez API
    print("[3/3] Charted Space (API travellermap)")
    for name in CHARTED_SECTORS:
        q = urllib.parse.quote(name)
        tab_url = f"{TM_BASE}/data/{q}/tab"
        meta_url = f"{TM_BASE}/api/metadata?sector={q}"
        tab = fetch(tab_url, RAW_DIR / f"{name}.tab", skip_existing)
        meta_raw = fetch(meta_url, RAW_DIR / f"{name}.metadata.json", skip_existing)
        try:
            meta = json.loads(meta_raw)
        except json.JSONDecodeError:
            meta = {}
        rows = parse_tab(tab.decode("utf-8", errors="replace"))
        sectors_out[name] = {
            "name": name,
            "x": meta.get("X"),
            "y": meta.get("Y"),
            "milieu": "M1105",
            "data_status": "Official" if name == "Vland" else "OTU",
            "author": None,
            "source": "travellermap.com /data",
            "worlds_source": "tab",
            "worlds": normalize_worlds(rows),
        }
        manifest["sources"].append({"url": tab_url})
        print(f"      {name:<28} swiatow: {len(sectors_out[name]['worlds'])}")

    (OUT_DIR / "sectors.json").write_text(
        json.dumps(sectors_out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    manifest["sector_count"] = len(sectors_out)
    manifest["missing"] = missing
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nOK: {len(sectors_out)} sektorow -> {OUT_DIR / 'sectors.json'}")
    if missing:
        print(f"UWAGA, brakujace: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
