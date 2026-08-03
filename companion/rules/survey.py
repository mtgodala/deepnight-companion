"""Survey Index i skanowanie (B3 p.71-76; spec §1-§2, §4)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from . import tables
from .dice import roll


@dataclass
class SweepResult:
    mode: str
    si_before: int
    si_after: int
    gain: int
    applied: bool          # False gdy zasada "largest increase" skasowala przyrost
    time_amount: int
    time_unit: str         # "min" / "h"
    reveals_ship: bool
    dice_log: dict


def initial_si(rng: random.Random | None = None) -> int:
    """Startowe SI hexu przy pierwszym zainteresowaniu: D3 (B3 p.71)."""
    return roll("D3", rng)


def apply_sweep(
    si: int,
    mode: str,
    best_sweep_gain: int = 0,
    effect: int | None = None,
    rng: random.Random | None = None,
) -> SweepResult:
    """Wykonuje sweep systemu i stosuje zasade "liczy sie najwiekszy przyrost".

    si              - biezacy SI hexu
    best_sweep_gain - najwiekszy dotychczasowy przyrost ze sweepow TEGO hexu
                      (B3 p.73: Active +2 potem Full +4 daje lacznie +4, nie +6)
    effect          - Effect checku dla trybu "remote" (SI += 2*Effect, B3 p.72)
    """
    spec = tables.SURVEY_MODES[mode]
    dice_log: dict = {}

    if mode == "remote":
        if effect is None:
            raise ValueError("tryb remote wymaga effect z checku Average(8+)")
        gain = max(0, 2 * effect)
    elif mode == "passive":
        gain = 1
    elif mode == "active":
        gain = roll("D3", rng)
        dice_log["si_gain"] = gain
    elif mode == "full":
        gain = roll("1D", rng)
        dice_log["si_gain"] = gain
    else:
        raise ValueError(f"nieznany tryb: {mode}")

    time_amount = roll(spec["time"][0], rng)
    dice_log["time"] = time_amount

    # Zasada largest-increase (B3 p.73): sweep nadpisuje slabszy sweep,
    # nie sumuje sie z nim. SI liczone od poziomu sprzed serii sweepow.
    applied = gain > best_sweep_gain
    base = si - best_sweep_gain
    new_si = min(tables.SI_MAX, base + max(gain, best_sweep_gain))

    return SweepResult(
        mode=mode, si_before=si, si_after=new_si, gain=gain, applied=applied,
        time_amount=time_amount, time_unit=spec["time"][1],
        reveals_ship=spec["reveals_ship"], dice_log=dice_log,
    )


def dwell_gain(days_in_system: int, rng: random.Random | None = None) -> int:
    """Pobyt w systemie: +1 SI co 1D dni zbierania danych (B3 p.74).

    Zwraca przyrost SI za `days_in_system` dni (symuluje kolejne interwaly 1D).
    Kumuluje sie NIEZALEZNIE od sweepow (decyzja HR, spec §13).
    """
    gain = 0
    remaining = days_in_system
    while remaining > 0:
        interval = roll("1D", rng)
        if interval > remaining:
            break
        remaining -= interval
        gain += 1
    return gain


def revealed_keys(si: int) -> list[str]:
    """Co jest widoczne dla graczy przy danym SI (B3 p.71) - kumulatywnie."""
    keys: list[str] = []
    for level in range(min(si, tables.SI_MAX) + 1):
        keys.extend(tables.SI_REVEALS[level])
    return keys


def deep_space_threshold(body_type: str, distance_pc: int) -> int:
    """Prog scan-points na detekcje ciala w hexie odleglym o distance_pc (B3 p.74)."""
    return tables.DEEP_SPACE_DETECTION[body_type] + distance_pc


def short_range_detection(
    dm_flags: list[str],
    parsecs_to_nearest_system: int,
    rng: random.Random | None = None,
) -> dict:
    """Short-Range Detection po skoku w pusty hex (B3 p.75)."""
    dm = sum(tables.SHORT_RANGE_DM[f] for f in dm_flags)
    dm += tables.SHORT_RANGE_DM["per_parsec_to_nearest_system"] * parsecs_to_nearest_system
    total = roll("2D", rng) + dm
    for (lo, hi), objects in tables.SHORT_RANGE_RESULTS:
        if lo <= total <= hi:
            if objects == "1D3":
                count = roll("1D3", rng)
            elif objects == "1D_plus_over12":
                count = roll("1D", rng) + max(0, total - 12)
            else:
                count = objects
            break
    sweep_days = roll(tables.SHORT_RANGE_SWEEP_DAYS, rng)
    found = [nature_of_object(rng) for _ in range(count)]
    return {"roll_total": total, "dm": dm, "count": count,
            "sweep_days": sweep_days, "objects": found}


def nature_of_object(rng: random.Random | None = None) -> dict:
    """Nature of Objects Found (B3 p.76)."""
    r = roll("2D", rng)
    if r == 2:
        sub = roll("1D", rng)
        return {"roll": r, "sub": sub, "kind": "unusual",
                "desc": tables.NATURE_SUB_2[sub]}
    if r == 12:
        sub = roll("1D", rng)
        return {"roll": r, "sub": sub, "kind": "large_rogue",
                "desc": tables.NATURE_SUB_12[sub]}
    for key, (kind, desc) in tables.NATURE_OF_OBJECTS.items():
        if isinstance(key, tuple) and key[0] <= r <= key[1]:
            return {"roll": r, "kind": kind, "desc": desc}
    raise AssertionError("nieosiagalne")
