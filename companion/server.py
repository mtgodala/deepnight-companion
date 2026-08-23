"""Deepnight Companion - serwer (FastAPI, localhost, laptop przy stole).

Uruchomienie:  .venv/Scripts/python.exe -m uvicorn companion.server:app --port 8010
UI graczy:     http://localhost:8010/

Widok graczy NIE dostaje pol gm_* ani danych ponad prog Survey Index.
Tryb GM: naglowek X-GM-Token o wartosci z companion/gm_token.txt
(plik generowany przy pierwszym starcie; nie pokazywac graczom).
"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .rules import checks, jump, survey, sysgen, tables
from .rules.dice import roll

import os

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("DEEPNIGHT_STATE_DIR", ROOT / "state"))
DATA = ROOT / "companion" / "data" / "sectors"
WEB = ROOT / "companion" / "web"
SHIP_LOG_DIR = STATE / "journal" / "ship-log"
GM_TOKEN_FILE = Path(os.environ.get("DEEPNIGHT_GM_TOKEN_FILE",
                                    ROOT / "companion" / "gm_token.txt"))

DAYS_PER_YEAR = 365  # kalendarz imperialny: dni 001-365

app = FastAPI(title="Deepnight Companion")

# ---------------------------------------------------------------- utils/state

_sectors: dict[str, Any] = {}
_by_coords: dict[tuple[int, int], str] = {}


def load_sectors() -> None:
    global _sectors, _by_coords
    _sectors = json.loads((DATA / "sectors.json").read_text(encoding="utf-8"))
    _by_coords = {(s["x"], s["y"]): name for name, s in _sectors.items()}


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# migracja stanu z wczesniejszych wersji (brakujace klucze -> defaulty)
SHIP_DEFAULTS = {
    "rare_materials": 0, "rare_biologicals": 0, "exotic_materials": 0,
    "trail": None,  # None -> [pozycja]
    "defects": [], "breakdowns": [], "failures": [], "detected_by": [],
}


def ship() -> dict:
    s = _read_json(STATE / "ship.json", None)
    if s is None:
        raise HTTPException(409, "Kampania niezainicjowana - POST /api/init")
    for k, v in SHIP_DEFAULTS.items():
        if k not in s or s[k] is None:
            s[k] = [dict(s["position"])] if k == "trail" else (list(v) if isinstance(v, list) else v)
    return s


def save_ship(s: dict) -> None:
    _write_json(STATE / "ship.json", s)


def survey_state() -> dict:
    return _read_json(STATE / "survey.json", {"si": {}, "best_sweep": {},
                                              "deep_scan": {}, "dwell_days": {}})


def save_survey(s: dict) -> None:
    _write_json(STATE / "survey.json", s)


UNDO_DIR = STATE / ".undo"
UNDO_KEEP = 15


def snapshot(action: str) -> None:
    """Zrzut ship.json + survey.json przed akcja mutujaca (undo przy stole)."""
    UNDO_DIR.mkdir(parents=True, exist_ok=True)
    snap = {
        "ts": time.time(),
        "action": action,
        "ship": _read_json(STATE / "ship.json", None),
        "survey": _read_json(STATE / "survey.json", None),
        "crew": _read_json(STATE / "crew.json", None),
        "cargo": _read_json(STATE / "cargo.json", None),
    }
    existing = sorted(UNDO_DIR.glob("*.json"))
    n = int(existing[-1].stem.split("-")[0]) + 1 if existing else 1
    _write_json(UNDO_DIR / f"{n:05d}-{action}.json", snap)
    for old in existing[:-UNDO_KEEP]:
        old.unlink()


def pop_snapshot() -> dict | None:
    existing = sorted(UNDO_DIR.glob("*.json"))
    if not existing:
        return None
    snap = json.loads(existing[-1].read_text(encoding="utf-8"))
    existing[-1].unlink()
    return snap


def gm_token() -> str:
    if not GM_TOKEN_FILE.exists():
        GM_TOKEN_FILE.write_text(secrets.token_hex(16), encoding="utf-8")
    return GM_TOKEN_FILE.read_text(encoding="utf-8").strip()


def is_gm(x_gm_token: str | None) -> bool:
    return bool(x_gm_token) and secrets.compare_digest(x_gm_token, gm_token())


def hex_key(sector: str, hex_: str) -> str:
    return f"{sector}:{hex_}"


def sector_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace(",", "")


# ------------------------------------------------------------------- dziennik

def log_event(kind: str, text: str, data: dict | None = None,
              gm_only: bool = False) -> None:
    SHIP_LOG_DIR.mkdir(parents=True, exist_ok=True)
    s = _read_json(STATE / "ship.json", {})
    rec = {
        "ts": time.time(),
        "date_imperial": s.get("date_imperial"),
        "kind": kind,
        "text": text,
        "data": data or {},
    }
    if gm_only:
        rec["gm_only"] = True
    with (SHIP_LOG_DIR / "log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_log(limit: int = 200) -> list[dict]:
    p = SHIP_LOG_DIR / "log.jsonl"
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    return [json.loads(ln) for ln in lines[-limit:]]


# ----------------------------------------------------------------------- czas

def advance_time(s: dict, hours: float, dwelling: bool = True) -> list[str]:
    """Przesuwa czas, nalicza SU (1000/dzien, B3 p.46) i pobyt (SI, B3 p.74).

    Zwraca liste komunikatow (np. przekroczone progi zapasow).
    """
    notes: list[str] = []
    s["hours_frac"] = s.get("hours_frac", 0.0) + hours
    days, s["hours_frac"] = divmod(s["hours_frac"], 24.0)
    days = int(days)
    if days:
        # data imperialna DDD-YYYY
        ddd, yyyy = s["date_imperial"].split("-")
        total = int(ddd) + days
        year = int(yyyy)
        while total > DAYS_PER_YEAR:
            total -= DAYS_PER_YEAR
            year += 1
        s["date_imperial"] = f"{total:03d}-{year}"
        s["mission_day"] = s.get("mission_day", 0) + days
        # zuzycie SU wg budzetu dziennego (B3 p.46-48)
        budget = s.get("supply_budget_per_day", tables.SHIP["supply_per_day"])
        s["supply_units"] = max(0, s["supply_units"] - budget * days)
        pct = round(100 * budget / tables.SHIP["supply_per_day"])
        effect, maint_dm = tables.lookup_band(tables.SUPPLY_LEVEL_EFFECTS,
                                              min(100, pct))
        if s["supply_units"] <= 0:
            notes.append("SUPPLY 0: brak zapasow - auto CEIM/MOR -1D co 2D dni (B3 p.49)")
        # paliwo reaktora: 900 t / 8 tygodni operacji = 112,5 t/tydz.
        # (B2 karta: zbiornik 27 900 = 27 000 na J-4 + 900 na operacje; spec par.0)
        if s.get("fuel_tons", 0) > 0:
            burn = days * tables.SHIP["powerplant_tons_per_week"] / 7
            s["fuel_tons"] = max(0.0, round(s["fuel_tons"] - burn, 1))
            if s["fuel_tons"] <= 0:
                notes.append("PALIWO 0: zbiorniki puste - reaktor bez rezerwy "
                             "(B2: 8 tygodni operacji)")
        # pobyt w systemie: +1 SI co 1D dni (B3 p.74) - prog losowany 1D
        # i utrwalany per hex (dwell_next), nie stala srednia
        if dwelling and s.get("position"):
            sv = survey_state()
            key = hex_key(s["position"]["sector"], s["position"]["hex"])
            sv["dwell_days"][key] = sv["dwell_days"].get(key, 0) + days
            gained = 0
            nxt = sv.setdefault("dwell_next", {}).get(key) or roll("1D")
            while sv["dwell_days"][key] >= nxt:
                sv["dwell_days"][key] -= nxt
                gained += 1
                nxt = roll("1D")
            sv["dwell_next"][key] = nxt
            if gained:
                cur = sv["si"].get(key, 0)
                sv["si"][key] = min(tables.SI_MAX, cur + gained)
                notes.append(f"Pobyt w systemie: SI +{gained} (B3 p.74)")
            save_survey(sv)
    return notes


# ------------------------------------------------------------------ widok gracza

def get_system_record(sector: str, hex_: str) -> dict:
    """Zwraca pelny rekord systemu (kanon lub generowany), tworzac go przy 1. uzyciu."""
    slug = f"{sector_slug(sector)}-{hex_}"
    path = STATE / "systems" / f"{slug}.json"
    rec = _read_json(path, None)
    if rec is not None:
        # backfill: starsze rekordy generowane bez listy cial -> regeneruj
        # (ten sam seed = te same wartosci bazowe) zachowujac pola GM
        if rec.get("generated") and not rec.get("empty") and "bodies_detail" not in rec:
            fresh = sysgen.generate_system(sector, hex_, star_known=True,
                                           region_type=rec.get("region_type", "rift"))
            for k in ("gm_notes", "gm_encounter", "gm_override"):
                fresh[k] = rec.get(k, fresh.get(k))
            _write_json(path, fresh)
            return fresh
        return rec
    sec = _sectors.get(sector)
    if sec is None:
        raise HTTPException(404, f"nieznany sektor: {sector}")
    world = sec["worlds"].get(hex_)
    if world and world["known"]:
        rec = sysgen.canonical_system(sector, hex_, world)
    elif world:  # gwiazda z dotmapy, system do wygenerowania
        rec = sysgen.generate_system(sector, hex_, star_known=True)
    elif sec.get("worlds_source") == "generate":
        rec = sysgen.generate_system(sector, hex_, star_known=False,
                                     region_type="rift")
    else:  # dotmapa istnieje, brak wiersza = pustka Szczeliny
        rec = {"sector": sector, "hex": hex_, "empty": True, "generated": False}
    _write_json(path, rec)
    return rec


def player_view(rec: dict, si: int) -> dict:
    """Filtruje rekord systemu wg SI (B3 p.71) i usuwa pola gm_*."""
    if rec.get("empty"):
        return {"sector": rec["sector"], "hex": rec["hex"],
                "empty": True, "si": si}
    if rec.get("canon"):
        # system kanoniczny = w katalogach wyprawy; dane jawne w calosci
        return {k: v for k, v in rec.items() if not k.startswith("gm_")} | {"si": si}
    if rec.get("gm_override"):
        rec = {**rec, **{k: v for k, v in rec["gm_override"].items()
                         if not k.startswith("gm_")}}
    out: dict[str, Any] = {"sector": rec["sector"], "hex": rec["hex"],
                           "empty": False, "si": si,
                           "canon": rec.get("canon", False)}
    keys = set(survey.revealed_keys(si))
    if "star_presence" in keys:
        out["star_presence"] = True
    if "star_types" in keys:
        out["stars"] = rec.get("stars", [])
    elif "star_class_general" in keys and rec.get("stars"):
        out["star_class_general"] = [s.split()[0][0] if s else "?"
                                     for s in rec["stars"]]
    if "gas_giants" in keys:
        out["gas_giant"] = rec.get("gas_giant")
    if "terrestrials" in keys:
        out["planetary_bodies"] = rec.get("planetary_bodies")
        out["planetoids"] = rec.get("planetoids")
    # lista cial wg SI: 5+ tylko gazowe olbrzymy, 6+ wszystkie ciala,
    # 7+ takze notki o warunkach (B3 p.71)
    if rec.get("bodies_detail"):
        vis = []
        for b in rec["bodies_detail"]:
            if b["kind"] == "gg" and si >= 5:
                pass
            elif si >= 6:
                pass
            else:
                continue
            vis.append({**b, "note": b["note"] if si >= 7 else ""})
        if vis:
            out["bodies_detail"] = vis
    if rec.get("deep_space_objects"):
        out["deep_space_objects"] = rec["deep_space_objects"]
    if "atmosphere_presence" in keys:
        out["habitable"] = rec.get("habitable")
        out["borderline_habitable"] = rec.get("borderline_habitable")
    uwp = rec.get("mainworld_uwp")
    if uwp:
        if "uwp_full" in keys:
            out["mainworld_uwp"] = uwp
            out["name"] = rec.get("name")
            out["bases"] = rec.get("bases", "")
            out["zone"] = rec.get("zone", "")
        elif "uwp_correct_shs" in keys:
            out["uwp_partial"] = uwp[:4] + "???" + uwp[7:]
        elif "uwp_estimate_shs" in keys:
            out["uwp_estimate"] = uwp[:4] + "???" + uwp[7:] + " (szacunek)"
    # kanoniczne nazwane systemy sa na mapie wyprawy od poczatku
    if rec.get("canon") and rec.get("name"):
        out["name"] = rec.get("name")
    return out


def baseline_si(sector: str, hex_: str, sv: dict) -> int:
    """SI hexu: zapisane, albo baza z mapy gwiezdnej (dotmapa = SI 1, B3 p.71)."""
    key = hex_key(sector, hex_)
    if key in sv["si"]:
        return sv["si"][key]
    sec = _sectors.get(sector)
    if sec and sec.get("worlds_source") != "generate":
        return 1  # ekspedycja MA mape gwiazd tego sektora
    return 0


# -------------------------------------------------------------------- modele

class InitBody(BaseModel):
    start: str = "giikur"           # "giikur" | "demnan"
    date_imperial: str = "001-1105"
    mor_roll: int | None = None     # 2D3; None = rzuc automatycznie


class ScanBody(BaseModel):
    sector: str
    hex: str
    mode: str                       # remote|passive|active|full


class JumpBody(BaseModel):
    sector: str
    hex: str
    env_flags: list[str] = []


class SkimBody(BaseModel):
    tons: float
    mode: str = "deep"              # deep|safe|ice (ice = kometa/cialo lodowe)


class WaitBody(BaseModel):
    days: int


class NoteBody(BaseModel):
    text: str
    author: str = ""


START_POSITIONS = {
    "giikur": {"sector": "Vland", "hex": "0211"},
    "demnan": {"sector": "Incognita Citerior", "hex": "3124"},
}


# ------------------------------------------------------------------ endpoints

@app.on_event("startup")
def _startup() -> None:
    load_sectors()
    gm_token()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.post("/api/init")
def init_campaign(body: InitBody) -> dict:
    if (STATE / "ship.json").exists():
        raise HTTPException(409, "ship.json juz istnieje - usun recznie, by zresetowac")
    pos = START_POSITIONS.get(body.start)
    if not pos:
        raise HTTPException(400, "start: giikur|demnan")
    mor_roll = body.mor_roll if body.mor_roll is not None else roll("2D3")
    s = {
        "position": pos,
        "date_imperial": body.date_imperial,
        "mission_day": 0,
        "fuel_tons": tables.SHIP["fuel_tank_tons"],
        "supply_units": tables.SHIP["supply_capacity"],
        "supply_budget_per_day": tables.SHIP["supply_per_day"],
        "hull_pct": 100,
        "cei": tables.SHIP["starting_cei"],          # B2: CEI 7
        "ceim": tables.SHIP["starting_ceim"],
        "mor": tables.SHIP["starting_cei"] + mor_roll,  # CEI + 2D3 (B3 p.38)
        "cfi": 0,
        "dei": {"flight": 7, "engineering": 7, "operations": 7, "mission": 7},
        "rare_materials": 0, "rare_biologicals": 0, "exotic_materials": 0,
        "defects": [], "breakdowns": [], "failures": [],
        "detected_by": [],   # kto wykryl statek (aktywne skany)
        "trail": [pos],      # historia pozycji (rysowana na mapie)
        "hours_frac": 0.0,
    }
    save_ship(s)
    log_event("init", f"Poczatek kampanii companiona. Pozycja: {pos['sector']} {pos['hex']}, "
                      f"data {body.date_imperial}. CEI 7, MOR {s['mor']}.")
    return s


@app.get("/api/state")
def get_state() -> dict:
    s = ship()
    return {**s, "ship_constants": tables.SHIP}


@app.get("/api/sectors")
def list_sectors() -> list[dict]:
    return [{"name": n, "x": s["x"], "y": s["y"],
             "worlds_source": s.get("worlds_source", "dotmap"),
             "data_status": s.get("data_status")}
            for n, s in _sectors.items()]


@app.get("/api/sector/{name}")
def sector_map(name: str) -> dict:
    sec = _sectors.get(name)
    if sec is None:
        raise HTTPException(404, "nieznany sektor")
    sv = survey_state()
    s = ship()
    hexes = {}
    if sec.get("worlds_source") == "generate":
        # brak dotmapy: pokazujemy tylko hexy, ktore juz zeskanowano
        for key, si in sv["si"].items():
            ksec, khex = key.rsplit(":", 1)
            if ksec == name:
                rec = get_system_record(name, khex)
                hexes[khex] = player_view(rec, si)
    else:
        for hex_ in sec["worlds"]:
            si = baseline_si(name, hex_, sv)
            rec_summary: dict[str, Any] = {"si": si, "star_presence": True}
            w = sec["worlds"][hex_]
            if w["known"]:
                # kanoniczne systemy sa na mapie wyprawy (nazwa+UWP od startu)
                rec_summary.update({"name": w["name"], "uwp": w["uwp"],
                                    "bases": w["bases"], "zone": w["zone"],
                                    "stars": [w["stellar"]] if w.get("stellar") else [],
                                    "gas_giant": (w["gg"] > 0) if w.get("gg") is not None else None,
                                    "canon": True})
            elif si >= 3:
                rec = get_system_record(name, hex_)
                rec_summary["stars"] = rec.get("stars", [])
            if si >= 5:
                rec = get_system_record(name, hex_)
                rec_summary["gas_giant"] = rec.get("gas_giant")
            if si >= 6:  # SI 6 ujawnia pelna liste cial (B3 p.71)
                rec = get_system_record(name, hex_)
                rec_summary["n_bodies"] = len(rec.get("bodies_detail") or [])
            hexes[hex_] = rec_summary
    here = None
    if s["position"]["sector"] == name:
        here = s["position"]["hex"]
    neighbors = {
        "left": _by_coords.get((sec["x"] - 1, sec["y"])),
        "right": _by_coords.get((sec["x"] + 1, sec["y"])),
        "up": _by_coords.get((sec["x"], sec["y"] - 1)),
        "down": _by_coords.get((sec["x"], sec["y"] + 1)),
    }
    return {"name": name, "x": sec["x"], "y": sec["y"],
            "data_status": sec.get("data_status"),
            "worlds_source": sec.get("worlds_source", "dotmap"),
            "hexes": hexes, "ship_hex": here, "neighbors": neighbors}


@app.get("/api/system/{sector}/{hex_}")
def system_detail(sector: str, hex_: str,
                  x_gm_token: str | None = Header(default=None)) -> dict:
    rec = get_system_record(sector, hex_)
    if is_gm(x_gm_token):
        return {"gm": True, **rec}
    sv = survey_state()
    return player_view(rec, baseline_si(sector, hex_, sv))


@app.post("/api/action/scan")
def action_scan(body: ScanBody) -> dict:
    s = ship()
    # Survey pasywny/aktywny/pelny robi sie Z WNETRZA systemu (B3 p.72-74);
    # jedyny skan na dystans to zdalny sweep (B3 p.72).
    if body.mode != "remote" and (s["position"]["sector"] != body.sector
                                  or s["position"]["hex"] != body.hex):
        raise HTTPException(400, "Survey pasywny/aktywny/pełny wymaga obecności "
                                 "w systemie — z dystansu działa tylko zdalny "
                                 "sweep (B3 p.72-73)")
    snapshot("scan")
    sv = survey_state()
    key = hex_key(body.sector, body.hex)
    si = baseline_si(body.sector, body.hex, sv)
    best = sv["best_sweep"].get(key, 0)

    check = None
    if body.mode == "remote":
        # check silnika: Average (8+) na DEI Mission/ECEI, DM+2 suite (B3 p.72).
        # Remote NIE wchodzi do puli largest-increase (B3 p.73 dotyczy tylko
        # passive/active/full) - przyrosty kumuluja sie ze sweepami na miejscu.
        chk = checks.remote_sweep_check(s)
        check = chk.as_dict()
        res = survey.apply_sweep(si, "remote",
                                 effect=max(0, chk.effect) if chk.success else 0)
    else:
        res = survey.apply_sweep(si, body.mode, best_sweep_gain=best)
        sv["best_sweep"][key] = max(best, res.gain)

    sv["si"][key] = res.si_after
    save_survey(sv)

    hours = (res.time_amount / 60 if res.time_unit == "min"
             else res.time_amount * 24 if res.time_unit == "d"
             else res.time_amount)
    notes = advance_time(s, hours)
    if res.reveals_ship:
        s.setdefault("detected_by", []).append(
            {"where": key, "date": s["date_imperial"]})
        notes.append("AKTYWNY SKAN: pozycja statku ujawniona nasluchujacym (B3 p.73)")
    save_ship(s)

    mode_pl = {"remote": "zdalny sweep", "passive": "pasywny survey",
               "active": "AKTYWNY survey", "full": "pelny survey"}[body.mode]
    log_event("scan", f"{mode_pl} {body.sector} {body.hex}: "
                      f"SI {res.si_before} -> {res.si_after} "
                      f"({res.time_amount} {res.time_unit})",
              {"mode": body.mode, "gain": res.gain, "applied": res.applied})
    return {"si_before": res.si_before, "si_after": res.si_after,
            "gain": res.gain, "applied": res.applied,
            "best_sweep": sv["best_sweep"].get(key, 0),
            "time": f"{res.time_amount} {res.time_unit}",
            "reveals_ship": res.reveals_ship, "notes": notes,
            "check": check, "rolls": res.dice_log,
            "view": player_view(get_system_record(body.sector, body.hex),
                                res.si_after)}


def world_to_sector_hex(w: tuple[int, int]) -> dict | None:
    """World-space -> {sector, hex}, o ile sektor istnieje w danych."""
    sx, sy = w[0] // 32, w[1] // 40
    name = _by_coords.get((sx, sy))
    if not name:
        return None
    return {"sector": name, "hex": f"{w[0] - sx * 32 + 1:02d}{w[1] - sy * 40 + 1:02d}"}


@app.post("/api/action/jump")
def action_jump(body: JumpBody) -> dict:
    snapshot("jump")
    s = ship()
    org = s["position"]
    org_sec, dst_sec = _sectors.get(org["sector"]), _sectors.get(body.sector)
    if dst_sec is None:
        raise HTTPException(404, "nieznany sektor docelowy")
    a = jump.hex_to_world(org_sec["x"], org_sec["y"], org["hex"])
    b = jump.hex_to_world(dst_sec["x"], dst_sec["y"], body.hex)
    plan = jump.plan_jump(a, b, s["fuel_tons"], body.env_flags)
    if not (plan.range_ok and plan.fuel_ok):
        raise HTTPException(400, "; ".join(plan.notes) or "skok niemozliwy")

    # skok w zaburzonej przestrzeni (mglawica/protogwiazda, B3 p.11-12):
    # check Average(8+) z env_dm; fail => misjump [HR - tabela w core MGT2]
    jump_chk = None
    misjump = None
    dest = {"sector": body.sector, "hex": body.hex}
    if plan.env_dm:
        jump_chk = checks.jump_check(s, plan.env_dm)
        if not jump_chk.success:
            cands = [c for c in (world_to_sector_hex(n)
                                 for n in jump.neighbors_world(b)) if c]
            drift_days = roll("1D")
            if cands:
                dest = cands[(roll("1D") - 1) % len(cands)]
            misjump = {"intended": {"sector": body.sector, "hex": body.hex},
                       "actual": dict(dest), "drift_days": drift_days}
            if jump_chk.total <= 2:
                s.setdefault("defects", []).append(
                    {"system": "j_drive", "note": "misjump - przeciazenie napedu"})

    s["fuel_tons"] -= plan.fuel_required
    s["position"] = dict(dest)
    s.setdefault("trail", []).append(dict(dest))
    # reset licznika pobytu w nowym hexie
    hours = plan.time_hours + (misjump["drift_days"] * 24 if misjump else 0)
    notes = advance_time(s, hours, dwelling=False)
    if misjump:
        notes.append(f"MISJUMP: wyjscie ze skoku w {dest['sector']} {dest['hex']} "
                     f"zamiast {body.sector} {body.hex}; korekta {misjump['drift_days']} dni; "
                     "zalecany check Erosion of Capabilities (B3 p.56) [HR]")
    save_ship(s)

    rec = get_system_record(dest["sector"], dest["hex"])
    sv = survey_state()
    key = hex_key(dest["sector"], dest["hex"])
    # Post-Jump Primary: Easy (4+) na ECEI (B3 p.63) - rzuca silnik
    pj = checks.post_jump_check(s)
    arrival_si = max(baseline_si(dest["sector"], dest["hex"], sv), 3 if pj.success else 2)
    if not pj.success:
        notes.append("Post-Jump Primary niepełny: dane systemu ograniczone, "
                     "powtórz procedury sensorowe (B3 p.63)")
    # positional check Routine: D3 minut; misjump wykryty niemal od razu (B3 p.73-74)
    positional = {"kind": "routine", "minutes": roll("D3"),
                  "confirmed": misjump is None}
    # automatyczny survey pasywny przy wejsciu do systemu (B3 p.73: "a system
    # survey is normally performed immediately"); pusty hex - nie ma czego skanowac
    passive = None
    if not rec.get("empty"):
        best = sv["best_sweep"].get(key, 0)
        res = survey.apply_sweep(arrival_si, "passive", best_sweep_gain=best)
        sv["best_sweep"][key] = max(best, res.gain)
        passive = {"si_before": res.si_before, "si_after": res.si_after,
                   "minutes": res.time_amount}
        arrival_si = res.si_after
    sv["si"][key] = arrival_si
    save_survey(sv)

    log_event("jump", f"Skok {org['sector']} {org['hex']} -> {dest['sector']} {dest['hex']} "
                      f"({plan.parsecs} pc, {plan.fuel_required} t paliwa, ~7 dni)"
                      + (" MISJUMP" if misjump else ""),
              {"parsecs": plan.parsecs, "fuel": plan.fuel_required,
               "env_dm": plan.env_dm, "misjump": bool(misjump)})
    out = {"plan": plan.__dict__, "position": s["position"],
           "fuel_tons": s["fuel_tons"], "date_imperial": s["date_imperial"],
           "notes": notes, "check": pj.as_dict(),
           "jump_check": jump_chk.as_dict() if jump_chk else None,
           "arrival": {"positional": positional, "passive": passive,
                       "misjump": misjump},
           "arrival_view": player_view(rec, arrival_si)}
    if rec.get("empty"):
        out["empty_hex"] = True
        out["notes"].append("Pusty hex: dostepna akcja Short-Range Detection (B3 p.75)")
    return out


@app.post("/api/action/security_sweep")
def action_security_sweep() -> dict:
    """Pelny security sweep statku: 2Dx30 min, Easy (4+) (B3 p.64-65)."""
    snapshot("security")
    s = ship()
    chk = checks.security_sweep_check(s)
    minutes = roll("2D") * 30
    notes = advance_time(s, minutes / 60)
    save_ship(s)
    log_event("security", f"Security sweep ({minutes} min): "
                          f"{'rzetelny' if chk.success else 'niedbaly'}")
    return {"minutes": minutes, "check": chk.as_dict(), "notes": notes,
            "date_imperial": s["date_imperial"]}


@app.post("/api/action/skim")
def action_skim(body: SkimBody) -> dict:
    snapshot("skim")
    s = ship()
    pos = s["position"]
    rec = get_system_record(pos["sector"], pos["hex"])
    ice_obj = None
    if body.mode == "ice":
        # tankowanie z komety/ciala lodowego znalezionego Short-Range Detection
        # (B3 p.70 + p.75-76); HR: tempo ogranicza procesor 4000 t/dzien
        for o in rec.get("deep_space_objects", []):
            if o.get("kind") in ("small_comet", "cometary_body") and not o.get("exhausted"):
                ice_obj = o
                break
        if ice_obj is None:
            raise HTTPException(400, "Brak znanej komety/ciala lodowego w tym hexie "
                                     "- najpierw Short-Range Detection (B3 p.75)")
    elif rec.get("empty") or not rec.get("gas_giant"):
        raise HTTPException(400, "Brak potwierdzonego gazowego olbrzyma w tym systemie "
                                 "(wymagane SI 5+ i obecnosc GG)")
    room = tables.SHIP["fuel_tank_tons"] - s["fuel_tons"]
    tons = min(body.tons, room)
    if tons <= 0:
        raise HTTPException(400, "Zbiorniki pelne")
    defects = sum(1 for d in s["defects"] if d.get("system") == "fuel_processors")
    extra_notes = []
    if body.mode == "ice":
        slowdown = 1 + 0.10 * defects
        plan = jump.SkimPlan(passes=0, tons_skimmed=int(tons), skim_time_min=0,
                             processing_days=round(
                                 tons / tables.SHIP["fuel_processor_tons_per_day"]
                                 * slowdown, 2),
                             pilot_dm=0, mode="ice")
        chk = checks.ice_refuel_check(s)
        if not chk.success:
            plan.processing_days = round(plan.processing_days * 1.5, 2)
            extra_notes.append("Operacja poszła opornie: czas +50%; zalecany check "
                               "Erosion of Capabilities (B3 p.56) [HR]")
        if ice_obj["kind"] == "small_comet":
            ice_obj["exhausted"] = True
            extra_notes.append("Kometa wyczerpana - starczyla na jedno tankowanie (B3 p.76)")
        _write_json(STATE / "systems" / f"{sector_slug(pos['sector'])}-{pos['hex']}.json", rec)
    else:
        plan = jump.plan_skim(tons, body.mode, processor_defects=defects)
        # check silnika: Mission na DEI Flight, glebokie warstwy DM-2 (B3 p.68)
        chk = checks.skim_check(s, body.mode)
        if not chk.success:
            plan.skim_time_min = int(plan.skim_time_min * 1.5)
            extra_notes.append("Operacja poszła opornie: czas +50%; zalecany check "
                               "Erosion of Capabilities (B3 p.56) [HR]")
    s["fuel_tons"] = min(tables.SHIP["fuel_tank_tons"],
                         s["fuel_tons"] + plan.tons_skimmed)
    hours = plan.skim_time_min / 60 + plan.processing_days * 24
    notes = advance_time(s, hours) + extra_notes
    save_ship(s)
    src = {"deep": "glebokie warstwy", "safe": "gorne warstwy",
           "ice": "lod z komety"}[body.mode]
    log_event("skim", f"Tankowanie ({src}): "
                      + (f"{plan.passes} passow, " if plan.passes else "")
                      + f"+{plan.tons_skimmed} t, "
                      f"przetwarzanie {plan.processing_days} dnia",
              plan.__dict__)
    return {"plan": plan.__dict__, "fuel_tons": s["fuel_tons"],
            "date_imperial": s["date_imperial"], "notes": notes,
            "check": chk.as_dict()}


@app.post("/api/action/wait")
def action_wait(body: WaitBody) -> dict:
    snapshot("wait")
    s = ship()
    notes = advance_time(s, body.days * 24)
    save_ship(s)
    log_event("wait", f"Postoj {body.days} dni w {s['position']['sector']} "
                      f"{s['position']['hex']}")
    return {"date_imperial": s["date_imperial"],
            "supply_units": s["supply_units"], "notes": notes}


@app.post("/api/undo")
def action_undo() -> dict:
    snap = pop_snapshot()
    if snap is None:
        raise HTTPException(404, "Brak akcji do cofniecia")
    if snap["ship"] is not None:
        _write_json(STATE / "ship.json", snap["ship"])
    if snap["survey"] is not None:
        _write_json(STATE / "survey.json", snap["survey"])
    # starsze snapshoty nie maja klucza "crew"/"cargo" — wtedy plik zostaje bez zmian
    if "crew" in snap:
        _write_json(STATE / "crew.json", snap["crew"] or {"people": []})
    if "cargo" in snap:
        _write_json(STATE / "cargo.json", snap["cargo"] or {"items": []})
    log_event("undo", f"Cofnieto akcje: {snap['action']} (korekta przy stole)")
    return {"undone": snap["action"], "state": ship()}


class ShortRangeBody(BaseModel):
    flags: list[str] = []           # known_interstellar_object / oort_cloud / kuiper_belt


def _nearest_star_pc(sector: str, hex_: str) -> int:
    """Odleglosc do najblizszej znanej gwiazdy (dotmapy, biezacy + sasiedzi)."""
    sec = _sectors.get(sector)
    origin = jump.hex_to_world(sec["x"], sec["y"], hex_)
    best = 99
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            name = _by_coords.get((sec["x"] + dx, sec["y"] + dy))
            if not name:
                continue
            nsec = _sectors[name]
            for h in nsec["worlds"]:
                d = jump.distance_pc(origin, jump.hex_to_world(nsec["x"], nsec["y"], h))
                if 0 < d < best:
                    best = d
    return best


@app.post("/api/action/shortrange")
def action_shortrange(body: ShortRangeBody) -> dict:
    """Short-Range Detection w pustym hexie (B3 p.75-76)."""
    snapshot("shortrange")
    s = ship()
    pos = s["position"]
    rec = get_system_record(pos["sector"], pos["hex"])
    if not rec.get("empty"):
        raise HTTPException(400, "Short-Range Detection ma sens tylko w pustym hexie (B3 p.75)")
    near = _nearest_star_pc(pos["sector"], pos["hex"])
    out = survey.short_range_detection(body.flags, near)
    # zapisz znaleziska w rekordzie hexu i przesun czas (1D dni sweepu)
    rec["deep_space_objects"] = out["objects"]
    _write_json(STATE / "systems" / f"{sector_slug(pos['sector'])}-{pos['hex']}.json", rec)
    notes = advance_time(s, out["sweep_days"] * 24)
    save_ship(s)
    found = ", ".join(o["desc"] or o["kind"] for o in out["objects"]) or "nic"
    log_event("shortrange", f"Short-Range Detection {pos['sector']} {pos['hex']}: "
                            f"{out['count']} obiekt(y) po {out['sweep_days']} dniach - {found}",
              {"roll": out["roll_total"]})
    return {**out, "nearest_star_pc": near, "notes": notes,
            "date_imperial": s["date_imperial"]}


# --- reczna edycja wspolczynnikow (eventy przy stole) ---

EDITABLE_FIELDS = {
    "cei": (0, 15), "ceim": (-6, 3), "mor": (0, 15), "cfi": (0, 30),
    "hull_pct": (0, 100),
    "fuel_tons": (0, tables.SHIP["fuel_tank_tons"]),
    "supply_units": (0, 10**9), "supply_budget_per_day": (0, 10**6),
    "rare_materials": (0, 10**6), "rare_biologicals": (0, 10**6),
    "exotic_materials": (0, 10**6),
    "dei.flight": (0, 15), "dei.engineering": (0, 15),
    "dei.operations": (0, 15), "dei.mission": (0, 15),
}


class EditBody(BaseModel):
    field: str
    value: float
    reason: str = ""


@app.post("/api/state/edit")
def edit_state(body: EditBody) -> dict:
    if body.field not in EDITABLE_FIELDS:
        raise HTTPException(400, f"pole nieedytowalne: {body.field}")
    lo, hi = EDITABLE_FIELDS[body.field]
    if not (lo <= body.value <= hi):
        raise HTTPException(400, f"wartosc poza zakresem [{lo}, {hi}]")
    snapshot("edit")
    s = ship()
    value = body.value if body.field in ("fuel_tons",) else int(body.value)
    if "." in body.field:
        parent, child = body.field.split(".", 1)
        old = s[parent][child]
        s[parent][child] = value
    else:
        old = s[body.field]
        s[body.field] = value
    save_ship(s)
    why = f" — {body.reason}" if body.reason else ""
    log_event("edit", f"Zmiana {body.field}: {old} -> {value}{why}")
    return {"field": body.field, "old": old, "new": value}


class DefectBody(BaseModel):
    op: str                  # add | remove
    kind: str                # defect | breakdown | failure
    system: str              # np. fuel_processors, m_drive, hull
    note: str = ""


@app.post("/api/state/defect")
def edit_defect(body: DefectBody) -> dict:
    key = {"defect": "defects", "breakdown": "breakdowns",
           "failure": "failures"}.get(body.kind)
    if not key or body.op not in ("add", "remove"):
        raise HTTPException(400, "op: add|remove, kind: defect|breakdown|failure")
    snapshot("defect")
    s = ship()
    lst = s.setdefault(key, [])
    if body.op == "add":
        lst.append({"system": body.system, "note": body.note,
                    "date": s["date_imperial"]})
        log_event("edit", f"Nowy {body.kind}: {body.system}"
                          f"{' — ' + body.note if body.note else ''}")
    else:
        idx = next((i for i, d in enumerate(lst) if d["system"] == body.system), None)
        if idx is None:
            raise HTTPException(404, f"brak {body.kind} dla {body.system}")
        lst.pop(idx)
        log_event("edit", f"Usunieto {body.kind}: {body.system} (naprawa)")
    save_ship(s)
    return {key: lst}


class BookmarkBody(BaseModel):
    sector: str
    hex: str
    label: str = ""


@app.get("/api/bookmarks")
def list_bookmarks() -> list[dict]:
    return _read_json(STATE / "bookmarks.json", [])


@app.post("/api/bookmarks")
def toggle_bookmark(body: BookmarkBody) -> dict:
    """Pin hexu ('Chart this world') - toggle; zapis w state/bookmarks.json."""
    marks = _read_json(STATE / "bookmarks.json", [])
    idx = next((i for i, m in enumerate(marks)
                if m["sector"] == body.sector and m["hex"] == body.hex), None)
    if idx is None:
        marks.append({"sector": body.sector, "hex": body.hex,
                      "label": body.label, "ts": time.time()})
        added = True
    else:
        marks.pop(idx)
        added = False
    _write_json(STATE / "bookmarks.json", marks)
    return {"added": added, "bookmarks": marks}


@app.get("/api/journal")
def get_journal(limit: int = 200,
                x_gm_token: str | None = Header(default=None)) -> list[dict]:
    rows = read_log(limit)
    if is_gm(x_gm_token):
        return rows
    return [r for r in rows if not r.get("gm_only")]


@app.post("/api/journal")
def add_note(body: NoteBody) -> dict:
    log_event("note", body.text, {"author": body.author})
    return {"ok": True}


# -------------------------------------------------------------- zaloga (crew)

CREW_TEMPLATE = ROOT / "companion" / "data" / "crew_template.json"
CREW_STATUSES = ("alive", "wounded", "dead", "missing")


def crew_state() -> dict:
    return _read_json(STATE / "crew.json", {"people": []})


class CrewPersonBody(BaseModel):
    slug: str                      # kebab-case, klucz osoby
    name: str = ""                 # puste przy delete
    node: str = ""                 # id stanowiska z crew_template.json
    kind: str = "npc"              # npc | pc
    status: str = "alive"          # alive | wounded | dead | missing
    note: str = ""                 # player-safe
    gm_note: str = ""              # tylko tryb GM
    delete: bool = False
    log_gm_only: bool = False      # wpis w dzienniku widoczny tylko dla GM


@app.get("/api/crew")
def get_crew(x_gm_token: str | None = Header(default=None)) -> dict:
    """Drzewo stanowisk (szablon B2 s.42-45) + obsada imienna (state/crew.json).

    Bez naglowka GM pola gm_* sa wyciete — jak wszedzie w companionie.
    """
    tpl = _read_json(CREW_TEMPLATE, {"nodes": []})
    gm = is_gm(x_gm_token)
    people = [p if gm else {k: v for k, v in p.items() if not k.startswith("gm_")}
              for p in crew_state().get("people", [])]
    return {"nodes": tpl["nodes"], "people": people, "gm": gm}


@app.post("/api/crew/person")
def crew_person(body: CrewPersonBody,
                x_gm_token: str | None = Header(default=None)) -> dict:
    """Upsert osoby na drzewie zalogi (otwarte przy stole, jak edycja statow).

    Bez trybu GM: nie mozna usuwac, pole gm_note jest ignorowane (istniejace
    zostaje), a wpis do dziennika zawsze jawny.
    """
    gm = is_gm(x_gm_token)
    if body.delete and not gm:
        raise HTTPException(403, "Usuwanie wymaga trybu GM (X-GM-Token)")
    if not gm:
        body.log_gm_only = False
    if body.status not in CREW_STATUSES:
        raise HTTPException(422, f"status musi byc jednym z {CREW_STATUSES}")
    tpl = _read_json(CREW_TEMPLATE, {"nodes": []})
    node_ids = {n["id"] for n in tpl["nodes"]}
    if not body.delete and body.node not in node_ids:
        raise HTTPException(422, "nieznane stanowisko (node)")
    snapshot("crew")
    st = crew_state()
    people = st.setdefault("people", [])
    idx = next((i for i, p in enumerate(people) if p["slug"] == body.slug), None)
    if body.delete:
        if idx is None:
            raise HTTPException(404, "brak osoby o tym slugu")
        removed = people.pop(idx)
        log_event("crew", f"Zaloga: {removed.get('name', body.slug)} usunieto z ewidencji",
                  gm_only=body.log_gm_only)
    else:
        old_gm_note = people[idx].get("gm_note", "") if idx is not None else ""
        person = {"slug": body.slug, "name": body.name, "node": body.node,
                  "kind": body.kind, "status": body.status, "note": body.note,
                  "gm_note": body.gm_note if gm else old_gm_note}
        if idx is None:
            people.append(person)
            log_event("crew", f"Zaloga: {body.name} — przydzial: {body.node}",
                      gm_only=body.log_gm_only)
        else:
            old = people[idx]
            people[idx] = person
            changes = []
            if old.get("node") != body.node:
                changes.append(f"przydzial {old.get('node')} -> {body.node}")
            if old.get("status") != body.status:
                changes.append(f"status {old.get('status')} -> {body.status}")
            log_event("crew", f"Zaloga: {body.name} — " +
                      ("; ".join(changes) if changes else "aktualizacja wpisu"),
                      gm_only=body.log_gm_only)
    _write_json(STATE / "crew.json", st)
    return {"ok": True, "people": len(people)}


# ------------------------------------------------------------ ladownia (cargo)
# Manifest ladowni: pozycje pogrupowane, kazda przypisana (opcjonalnie) do
# konkretnej ladowni (bay). Pojemnosci wg stat blockow podow (B2 p.34-39).
# Standardowe wyposazenie (bron, skafandry, sondy) NIE zajmuje cargo —
# manifest dotyczy tylko rzeczy ponad standard (pojazdy, moduly bazy,
# dodatkowe SU, znaleziska, materialy specjalne).

CARGO_BAYS = {
    "hangar-l": {"name_pl": "Hangar pod — lewa burta",
                 "name_en": "Hangar pod — port", "tons": 467.8},
    "hangar-p": {"name_pl": "Hangar pod — prawa burta",
                 "name_en": "Hangar pod — starboard", "tons": 467.8},
    "sci-l": {"name_pl": "Scientific pod — lewa burta",
              "name_en": "Scientific pod — port", "tons": 14.4},
    "sci-p": {"name_pl": "Scientific pod — prawa burta",
              "name_en": "Scientific pod — starboard", "tons": 14.4},
    "mission-l": {"name_pl": "Mission pod — lewa burta",
                  "name_en": "Mission pod — port", "tons": 841.6},
    "mission-p": {"name_pl": "Mission pod — prawa burta",
                  "name_en": "Mission pod — starboard", "tons": 841.6},
}
CARGO_CAPACITY = round(sum(b["tons"] for b in CARGO_BAYS.values()), 1)
CARGO_GROUPS = ("supplies", "vehicles", "base", "equipment",
                "materials", "salvage", "other")


def cargo_state() -> dict:
    return _read_json(STATE / "cargo.json", {"items": []})


class CargoItemBody(BaseModel):
    id: str                        # kebab-case, klucz pozycji
    name: str = ""                 # puste przy delete
    group: str = "other"           # klucz z CARGO_GROUPS
    bay: str = ""                  # klucz z CARGO_BAYS albo "" (nieprzypisane)
    qty: float = 1                 # liczba sztuk
    tons_each: float = 0.0         # tonaz za sztuke
    note: str = ""                 # player-safe
    gm_note: str = ""              # tylko tryb GM
    delete: bool = False
    log_gm_only: bool = False


def _cargo_usage(items: list[dict]) -> tuple[float, dict[str, float]]:
    per_bay = {k: 0.0 for k in CARGO_BAYS}
    total = 0.0
    for it in items:
        tons = round(it.get("qty", 0) * it.get("tons_each", 0.0), 1)
        total += tons
        if it.get("bay") in per_bay:
            per_bay[it["bay"]] += tons
    return round(total, 1), {k: round(v, 1) for k, v in per_bay.items()}


@app.get("/api/cargo")
def get_cargo(x_gm_token: str | None = Header(default=None)) -> dict:
    """Manifest ladowni + pojemnosci. Bez naglowka GM pola gm_* sa wyciete."""
    gm = is_gm(x_gm_token)
    raw = cargo_state().get("items", [])
    items = [i if gm else {k: v for k, v in i.items() if not k.startswith("gm_")}
             for i in raw]
    used, per_bay = _cargo_usage(raw)
    return {"items": items, "bays": CARGO_BAYS, "groups": list(CARGO_GROUPS),
            "capacity": CARGO_CAPACITY, "used": used, "per_bay": per_bay,
            "gm": gm}


@app.post("/api/cargo/item")
def cargo_item(body: CargoItemBody,
               x_gm_token: str | None = Header(default=None)) -> dict:
    """Upsert/delete pozycji manifestu (otwarte przy stole — ewidencja
    kwatermistrza; kazda zmiana idzie do dziennika i pod undo)."""
    gm = is_gm(x_gm_token)
    if not gm:
        body.log_gm_only = False
    if body.group not in CARGO_GROUPS:
        raise HTTPException(422, f"group musi byc jednym z {CARGO_GROUPS}")
    if body.bay and body.bay not in CARGO_BAYS:
        raise HTTPException(422, "nieznana ladownia (bay)")
    if body.qty < 0 or body.tons_each < 0:
        raise HTTPException(422, "qty i tons_each musza byc >= 0")
    snapshot("cargo")
    st = cargo_state()
    items = st.setdefault("items", [])
    idx = next((i for i, it in enumerate(items) if it["id"] == body.id), None)
    if body.delete:
        if idx is None:
            raise HTTPException(404, "brak pozycji o tym id")
        removed = items.pop(idx)
        log_event("cargo", f"Ladownia: zdjeto z manifestu — "
                  f"{removed.get('name', body.id)}", gm_only=body.log_gm_only)
    else:
        tons = round(body.qty * body.tons_each, 1)
        old_gm_note = items[idx].get("gm_note", "") if idx is not None else ""
        item = {"id": body.id, "name": body.name, "group": body.group,
                "bay": body.bay, "qty": body.qty, "tons_each": body.tons_each,
                "note": body.note,
                "gm_note": body.gm_note if gm else old_gm_note}
        if idx is None:
            items.append(item)
            log_event("cargo", f"Ladownia: przyjeto — {body.name} "
                      f"({body.qty} szt., {tons} t)", gm_only=body.log_gm_only)
        else:
            items[idx] = item
            log_event("cargo", f"Ladownia: aktualizacja — {body.name} "
                      f"({body.qty} szt., {tons} t)", gm_only=body.log_gm_only)
    used, _ = _cargo_usage(items)
    if used > CARGO_CAPACITY:
        log_event("cargo", f"UWAGA: manifest przekracza pojemnosc ladowni "
                  f"({used} t / {CARGO_CAPACITY} t)")
    _write_json(STATE / "cargo.json", st)
    return {"ok": True, "used": used, "capacity": CARGO_CAPACITY}


app.mount("/static", StaticFiles(directory=WEB), name="static")
