"""Kosci: rzuty losowe (gra) i deterministyczne (generacja swiata).

Notacja: "2D" = 2 x k6, "D3" = k3, "1D+4", "2Dx5", "3D-3".
Generacja systemow uzywa seeded_rng(sektor, hex) - ten sam hex zawsze
daje ten sam system (plan: determinizm).
"""

from __future__ import annotations

import hashlib
import random
import re

_DICE_RE = re.compile(r"^(\d*)D(3)?(?:([+x-])(\d+))?$", re.IGNORECASE)


def seeded_rng(*parts: str) -> random.Random:
    seed = hashlib.sha256(":".join(parts).encode("utf-8")).digest()
    return random.Random(seed)


def roll(spec: str, rng: random.Random | None = None) -> int:
    """Rzuca wg notacji ("2D", "D3", "1D+4", "2Dx5", "3D-3")."""
    rng = rng or random
    m = _DICE_RE.match(spec.strip())
    if not m:
        raise ValueError(f"zla notacja kosci: {spec!r}")
    count = int(m.group(1) or 1)
    sides = 3 if m.group(2) else 6
    total = sum(rng.randint(1, sides) for _ in range(count))
    op, num = m.group(3), m.group(4)
    if op == "+":
        total += int(num)
    elif op == "-":
        total -= int(num)
    elif op == "x":
        total *= int(num)
    return total


def roll_detail(spec: str, rng: random.Random | None = None) -> tuple[int, list[int]]:
    """Jak roll(), ale zwraca tez pojedyncze kosci (do logu/UI)."""
    rng = rng or random
    m = _DICE_RE.match(spec.strip())
    if not m:
        raise ValueError(f"zla notacja kosci: {spec!r}")
    count = int(m.group(1) or 1)
    sides = 3 if m.group(2) else 6
    dice = [rng.randint(1, sides) for _ in range(count)]
    total = sum(dice)
    op, num = m.group(3), m.group(4)
    if op == "+":
        total += int(num)
    elif op == "-":
        total -= int(num)
    elif op == "x":
        total *= int(num)
    return total, dice
