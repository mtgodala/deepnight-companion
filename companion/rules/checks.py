"""Symulator rzutow i checkow — wszystkie kosci gry dzieja sie tutaj.

Kazdy check zwraca pelne rozbicie (kosci + modyfikatory + prog + Effect),
zeby UI moglo pokazac graczom dokladnie, co sie wydarzylo.

Modyfikatory zalogi: tabela CEI -> task DM (B3 p.32). Do checkow dywizyjnych
uzywamy DEI danej dywizji + CEIM (B3 p.34: DEI podlega CEIM); gdy da sie
uzasadnic i CEI, i DEI - bierzemy WIEKSZY modyfikator (B3 p.34).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import tables


def cei_dm(value: int) -> int:
    """DM z tabeli CEI/DEI -> task DM (B3 p.32). Wartosci poza 0-15 sa przycinane."""
    return tables.CEI_DM[max(0, min(15, value))]


@dataclass
class CheckResult:
    label: str                 # co testujemy (PL)
    dice: list[int]            # wyrzucone kosci
    dms: list[tuple[str, int]]  # (opis modyfikatora, wartosc)
    target: int                # prog (np. 8 dla Average)
    total: int = 0
    success: bool = False
    effect: int = 0
    page: str = ""

    def __post_init__(self):
        self.total = sum(self.dice) + sum(v for _, v in self.dms)
        self.success = self.total >= self.target
        self.effect = self.total - self.target

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "dice": self.dice,
            "dms": [{"label": l, "value": v} for l, v in self.dms],
            "target": self.target,
            "total": self.total,
            "success": self.success,
            "effect": self.effect,
            "page": self.page,
        }


def roll_2d(rng: random.Random | None = None) -> list[int]:
    r = rng or random
    return [r.randint(1, 6), r.randint(1, 6)]


def division_dm(ship: dict, division: str, label: str | None = None) -> tuple[str, int]:
    """DM z DEI dywizji + CEIM (B3 p.34), opisany dla UI."""
    dei = ship.get("dei", {}).get(division, ship.get("cei", 7))
    eff = dei + ship.get("ceim", 0)
    return (label or f"DEI {division.capitalize()}{'+CEIM' if ship.get('ceim') else ''} ({eff})",
            cei_dm(eff))


def ecei_dm(ship: dict) -> tuple[str, int]:
    eff = ship.get("cei", 7) + ship.get("ceim", 0)
    return (f"ECEI ({eff})", cei_dm(eff))


def best_crew_dm(ship: dict, division: str) -> tuple[str, int]:
    """Wiekszy z DM(ECEI) i DM(DEI dywizji) — B3 p.34."""
    a, b = ecei_dm(ship), division_dm(ship, division)
    return a if a[1] >= b[1] else b


# ------------------------------------------------------------------ checki gry

def remote_sweep_check(ship: dict, extra_dms: list[tuple[str, int]] | None = None,
                       rng: random.Random | None = None) -> CheckResult:
    """Zdalny sweep: Average (8+) na DEI Mission/ECEI; DNR ma DM+2 za suite naukowy
    (B3 p.72). Sukces => SI += 2*Effect."""
    dms = [best_crew_dm(ship, "mission"), ("suite naukowy DNR", 2)]
    dms += extra_dms or []
    return CheckResult("Zdalny sweep sensorow", roll_2d(rng), dms, 8, page="B3 p.72")


def post_jump_check(ship: dict, rng: random.Random | None = None) -> CheckResult:
    """Post-Jump Primary: Easy (4+) na ECEI (B3 p.63)."""
    return CheckResult("Post-Jump Primary", roll_2d(rng), [ecei_dm(ship)], 4,
                       page="B3 p.63")


def skim_check(ship: dict, mode: str, rng: random.Random | None = None) -> CheckResult:
    """Skimming: abstrakcja Mission na DEI Flight (B3 p.68); glebokie warstwy DM-2.

    Skutek porazki (HR — B3 nie definiuje wprost): czas operacji +50%
    i zalecany check Erosion of Capabilities (B3 p.56).
    """
    dms = [division_dm(ship, "flight")]
    if mode == "deep":
        dms.append(("głębokie warstwy atmosfery", tables.SKIM_DEEP_PILOT_DM))
    return CheckResult("Skimming (operacja Dywizji Flight)", roll_2d(rng), dms, 8,
                       page="B3 p.68")


def ice_refuel_check(ship: dict, rng: random.Random | None = None) -> CheckResult:
    """Zbior lodu z komety/ciala lodowego (B3 p.70): operacja Dywizji Flight.

    HR — B3 nie podaje tempa poboru lodu; waskim gardlem jest procesor paliwa
    (B2: 4000 t/dzien). Porazka checku => czas +50% (jak skimming, HR).
    """
    return CheckResult("Zbiór lodu (operacja Dywizji Flight)", roll_2d(rng),
                       [division_dm(ship, "flight")], 8, page="B3 p.70")


def fuel_source_search_check(ship: dict, density: str,
                             rng: random.Random | None = None) -> CheckResult:
    """Szukanie zrodla paliwa w systemie (B3 p.69) na DEI Mission."""
    name, target, _, _ = tables.FUEL_SOURCE_CHECK[density]
    if target is None:
        raise ValueError("barren: uzyj Short-Range Detection (B3 p.69)")
    return CheckResult(f"Szukanie źródła paliwa ({name} {target}+)",
                       roll_2d(rng), [best_crew_dm(ship, "mission")], target,
                       page="B3 p.69")
