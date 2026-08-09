"""Skoki, paliwo, tankowanie (B2 karta + core MGT2 + B3 p.10-11, p.68-69; spec §0, §4, §5)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from . import tables
from .dice import roll


def hex_to_world(sector_x: int, sector_y: int, hex_: str) -> tuple[int, int]:
    """Hex sektora -> wspolrzedne world-space travellermap (spec Agent B).

    x = sx*32 + (hx-1); y = sy*40 + (hy-1). Core (0,0) = sektor Core.
    """
    hx, hy = int(hex_[:2]), int(hex_[2:])
    return sector_x * 32 + (hx - 1), sector_y * 40 + (hy - 1)


def _cube(p: tuple[int, int]) -> tuple[int, int, int]:
    """World-space (x,y) -> wspolrzedne cube siatki hex Travellera.

    Konwencja odd-q (pythonowe x%2 dziala tez dla ujemnych) zweryfikowana
    empirycznie na /api/jumpworlds (Giikur 0211, 10 swiatow, dystanse 1-4,
    w tym miedzysektorowe Corridor/Vland).
    """
    x, y = p
    q = x
    r = y - (x - (x % 2)) // 2
    return q, r, -q - r


def distance_pc(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Odleglosc w parsekach miedzy hexami world-space (metryka cube)."""
    aq, ar, as_ = _cube(a)
    bq, br, bs = _cube(b)
    return (abs(aq - bq) + abs(ar - br) + abs(as_ - bs)) // 2


def neighbors_world(p: tuple[int, int]) -> list[tuple[int, int]]:
    """6 hexow sasiadujacych (1 pc) w world-space — do zejscia z kursu przy misjumpie."""
    q, r, _ = _cube(p)
    out = []
    for dq, dr in ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)):
        nq, nr = q + dq, r + dr
        out.append((nq, nr + (nq - (nq % 2)) // 2))
    return out


@dataclass
class JumpPlan:
    parsecs: int
    fuel_required: int
    fuel_ok: bool
    range_ok: bool
    env_dm: int
    time_hours: int
    notes: list[str]


def plan_jump(
    origin_world: tuple[int, int],
    dest_world: tuple[int, int],
    fuel_on_board: float,
    env_flags: list[str] | None = None,
    rng: random.Random | None = None,
) -> JumpPlan:
    """Waliduje skok i liczy koszty. Nie modyfikuje stanu - to robi serwer."""
    pc = distance_pc(origin_world, dest_world)
    fuel_req = pc * tables.SHIP["fuel_per_parsec"]
    env_dm = sum(tables.JUMP_ENV_DM[f] for f in (env_flags or []))
    notes = []
    if pc > tables.SHIP["jump_rating"]:
        notes.append(f"Cel poza zasiegiem J-{tables.SHIP['jump_rating']} ({pc} pc)")
    if fuel_req > fuel_on_board:
        notes.append(f"Brak paliwa: potrzeba {fuel_req} t, jest {fuel_on_board:.0f} t")
    if env_dm:
        notes.append(f"Srodowiskowe DM do skoku: {env_dm} (B3 p.11)")
    return JumpPlan(
        parsecs=pc,
        fuel_required=fuel_req,
        fuel_ok=fuel_req <= fuel_on_board,
        range_ok=0 < pc <= tables.SHIP["jump_rating"],
        env_dm=env_dm,
        time_hours=tables.JUMP_TIME_HOURS,
        notes=notes,
    )


@dataclass
class SkimPlan:
    passes: int
    tons_skimmed: int
    skim_time_min: int
    processing_days: float
    pilot_dm: int
    mode: str


def plan_skim(
    tons_needed: float,
    mode: str = "deep",
    processor_defects: int = 0,
    rng: random.Random | None = None,
) -> SkimPlan:
    """Skimming gazowego olbrzyma (B3 p.68) + przetwarzanie (B2: 4000 t/dzien).

    mode: "deep" (750 t/pass, Pilot DM-2) lub "safe" (375 t/pass, bez DM).
    Defekt Fuel Processors: +10% czasu za kazdy (B3 p.55).
    """
    per_pass = (tables.SHIP["skim_tons_per_pass_deep"] if mode == "deep"
                else tables.SHIP["skim_tons_per_pass_safe"])
    passes = math.ceil(tons_needed / per_pass)
    tons = passes * per_pass
    skim_time = sum(roll("2D", rng) for _ in range(passes))
    processing_days = tons / tables.SHIP["fuel_processor_tons_per_day"]
    slowdown = 1 + 0.10 * processor_defects
    return SkimPlan(
        passes=passes,
        tons_skimmed=tons,
        skim_time_min=skim_time,
        processing_days=round(processing_days * slowdown, 2),
        pilot_dm=tables.SKIM_DEEP_PILOT_DM if mode == "deep" else 0,
        mode=mode,
    )


def fuel_source_check(density: str) -> dict:
    """Parametry checku szukania zrodla paliwa w systemie (B3 p.69)."""
    name, target, time_dice, unit = tables.FUEL_SOURCE_CHECK[density]
    return {"difficulty": name, "target": target,
            "time_dice": time_dice, "time_unit": unit,
            "skill": "Electronics (sensors) lub Science (cosmology)",
            "page": "B3 p.69"}
