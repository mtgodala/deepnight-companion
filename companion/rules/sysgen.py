"""Deterministyczna generacja systemow (B3 p.8, p.20-21 + core MGT2; spec §6).

Zasady podzialu:
- Obecnosc gwiazdy: dotmapa travellermap (kanon). Rzut Star System Presence
  TYLKO dla sektorow bez danych (worlds_source="generate").
- Zawartosc systemu (SDI, ciala, UWP, typ gwiazdy): generowana tutaj,
  seed = SHA256(sektor:hex) -> ten sam hex zawsze daje ten sam system.
- Kanon nadpisuje generator: hex z pelnym UWP w dotmapie = system kanoniczny.
- HR (spec §6): poza Charted Space Pop/Gov/Law = 0, starport X lub E -
  zgodne z kanonem (Demnan E567000-0). GM moze nadpisac polem gm_override.
"""

from __future__ import annotations

import random

from . import tables
from .dice import roll, seeded_rng

STARPORT_UNINHABITED = ("X", "E")  # HR: pustka Szczeliny; E gdy jest habitable

# Uproszczona tabela typow gwiazd wg rozkladu core MGT2 (2D, czestosci
# main-sequence); dokladne podtypy (0-9) losowane osobno.
_STAR_TYPE_2D = {
    2: "special",  # olbrzym/karzel bialy/inne - podtabela
    3: "M", 4: "M", 5: "M", 6: "M",
    7: "K", 8: "K",
    9: "G", 10: "G",
    11: "F",
    12: "hot",  # A/B
}
_SPECIAL_1D = {1: "White Dwarf", 2: "White Dwarf", 3: "Red Giant",
               4: "Red Giant", 5: "Brown Dwarf", 6: "Neutron Star"}
_HOT_1D = {1: "A", 2: "A", 3: "A", 4: "A", 5: "B", 6: "B"}


def star_presence(region_type: str, rng: random.Random) -> bool:
    """Czy w hexie jest gwiazda (B3 p.20) - tylko dla sektorow bez dotmapy."""
    target, dice = tables.STAR_PRESENCE[region_type]
    return roll(dice, rng) <= target


def gen_stars(rng: random.Random) -> list[str]:
    """Typ gwiazdy/gwiazd (uklad pojedynczy/podwojny/potrojny)."""
    n = 1
    r = roll("2D", rng)
    if r >= 10:
        n = 2
    if r == 12:
        n = 3
    stars = []
    for _ in range(n):
        t = _STAR_TYPE_2D[roll("2D", rng)]
        if t == "special":
            stars.append(_SPECIAL_1D[roll("1D", rng)])
        elif t == "hot":
            stars.append(f"{_HOT_1D[roll('1D', rng)]}{rng.randint(0, 9)} V")
        else:
            stars.append(f"{t}{rng.randint(0, 9)} V")
    return stars


def gen_sdi(rng: random.Random) -> int:
    """System Density Index: 3D-3, +1D-1 za kazda naturalna 6 (bez lancucha) (B3 p.20-21)."""
    dice = [rng.randint(1, 6) for _ in range(3)]
    sdi = sum(dice) - 3
    for d in dice:
        if d == 6:
            sdi += rng.randint(1, 6) - 1
    return sdi


def gen_specific_bodies(sdi: int, rng: random.Random) -> dict:
    """Specific Bodies (B3 p.21): pula DM = SDI, dzielona miedzy rzuty 1D+DM.

    Strategia silnika (przy generacji pelnej, nie "quick"): priorytet GG
    (paliwo!), potem planetoidy, potem habitable. Kazdy rzut dostaje min +1,
    pula sie wyczerpuje.
    """
    pool = sdi
    results = {}
    priority = ["gas_giant_refuel", "planetoids_mining",
                "borderline_habitable", "habitable"]
    for body in priority:
        if pool < 1:
            results[body] = None  # brak puli = brak pewnosci (nie: brak ciala)
            continue
        target = tables.SPECIFIC_BODIES[body]
        # przydziel tyle, ile potrzeba do sensownej szansy, max polowa puli+1
        alloc = min(pool, max(1, target - 3))
        pool -= alloc
        results[body] = roll("1D", rng) + alloc >= target
    return results


def gen_mainworld_uwp(rng: random.Random, habitable: bool) -> str:
    """UWP mainworldu: fizyczne cyfry wg core MGT2, spoleczne = 0 (HR spec §6)."""
    size = max(0, roll("2D", rng) - 2)
    atmo = max(0, roll("2D", rng) - 7 + size)
    if size <= 1:
        atmo = 0
    hydro = max(0, min(10, roll("2D", rng) - 7 + atmo))
    if size <= 1:
        hydro = 0
    if atmo <= 1 or atmo >= 10:
        hydro = max(0, hydro - 4)
    if habitable:
        # habitable = atmosfera oddychalna i woda (wymuszenie sensu)
        atmo = rng.choice([5, 6, 8])
        hydro = max(2, hydro)
        size = max(3, size)
    port = "E" if habitable else "X"
    hexd = "0123456789ABCDEFGH"
    return f"{port}{hexd[min(size, 17)]}{hexd[min(atmo, 17)]}{hexd[min(hydro, 17)]}000-0"


ZONES = {1: "wewnętrzna", 2: "wewnętrzna", 3: "ekosfera",
         4: "zewnętrzna", 5: "zewnętrzna", 6: "daleka"}
# typy swiatow per strefa (katalog B3 p.83-91), rzut 1D
_ZONE_TYPES = {
    "wewnętrzna": {1: ("world", "gorący świat skalny (hot rockball)", "powierzchnia spieczona, bez atmosfery lub śladowa"),
                   2: ("world", "gorący świat skalny (hot rockball)", ""),
                   3: ("world", "świat skalny (rockball)", ""),
                   4: ("world", "świat wulkaniczny", "aktywna tektonika, ryzykowne lądowanie"),
                   5: ("world", "świat pustynny", "sucho, możliwa rzadka atmosfera"),
                   6: ("world", "świat śladowy (trace world)", "resztkowa atmosfera")},
    "ekosfera": {1: ("world", "świat skalny (rockball)", ""),
                 2: ("world", "świat skalny (rockball)", ""),
                 3: ("world", "świat pustynny", "temperatury znośne, brak wody powierzchniowej"),
                 4: ("world", "świat wodny", "ocean pod atmosferą lub lodem"),
                 5: ("world", "super-ziemia", "grawitacja 1.2-2 g (B3 p.89)"),
                 6: ("world", "świat śladowy (trace world)", "")},
    "zewnętrzna": {1: ("world", "świat lodowy (iceball)", "lód wodny = potencjalne paliwo"),
                   2: ("world", "świat lodowy (iceball)", "lód wodny = potencjalne paliwo"),
                   3: ("world", "świat lodowy (iceball)", ""),
                   4: ("world", "gazowy karzeł (gas dwarf)", ""),
                   5: ("gg", "mały gazowy olbrzym", "skimming możliwy"),
                   6: ("world", "świat skalny (rockball)", "")},
    "daleka": {1: ("world", "świat lodowy (iceball)", ""),
               2: ("world", "świat lodowy (iceball)", ""),
               3: ("world", "świat lodowy (iceball)", ""),
               4: ("belt", "rozproszone planetoidy lodowe", "możliwe źródło paliwa"),
               5: ("world", "ciało przechwycone (captured body)", "nietypowa orbita"),
               6: ("world", "świat lodowy (iceball)", "")},
}


def gen_bodies_detail(rng: random.Random, n_bodies: int, bodies: dict,
                      habitable: bool) -> list[dict]:
    """Szczegolowa lista cial: co jest w systemie i w ktorej strefie.

    Wywolywana PO wszystkich dotychczasowych rzutach (ten sam strumien rng),
    wiec starsze pola rekordu pozostaja identyczne dla tego samego seeda.
    """
    detail: list[dict] = []
    placed = 0
    if bodies.get("gas_giant_refuel"):
        size = "duży" if roll("1D", rng) >= 3 else "mały"
        detail.append({"kind": "gg", "zone": "zewnętrzna",
                       "type": f"{size} gazowy olbrzym",
                       "note": "potwierdzone źródło paliwa (skimming, B3 p.68)"})
        placed += 1
    if bodies.get("planetoids_mining"):
        detail.append({"kind": "belt", "zone": "wewnętrzna" if roll("1D", rng) <= 2 else "zewnętrzna",
                       "type": "pas planetoid",
                       "note": "nadaje się do wydobycia surowców (B3 p.21)"})
        placed += 1
    if habitable:
        label = ("świat nadający się do życia" if bodies.get("habitable")
                 else "świat graniczny (borderline habitable)")
        detail.append({"kind": "world", "zone": "ekosfera", "type": label,
                       "note": "cel priorytetowy dla Dywizji Misji"})
        placed += 1
    for _ in range(max(0, n_bodies - placed)):
        zone = ZONES[roll("1D", rng)]
        kind, type_pl, note = _ZONE_TYPES[zone][roll("1D", rng)]
        detail.append({"kind": kind, "zone": zone, "type": type_pl, "note": note})
    order = {"wewnętrzna": 0, "ekosfera": 1, "zewnętrzna": 2, "daleka": 3}
    detail.sort(key=lambda b: order[b["zone"]])
    return detail


def generate_system(sector: str, hex_: str, *,
                    star_known: bool = True,
                    region_type: str = "rift") -> dict:
    """Pelna deterministyczna generacja zawartosci hexu.

    star_known=True  -> gwiazda jest w dotmapie (kanon); generujemy zawartosc.
    star_known=False -> najpierw rzut Star System Presence dla regionu.

    Zwraca pelny rekord z polami gm_* (do odfiltrowania w widoku graczy).
    """
    rng = seeded_rng("sysgen", sector, hex_)

    if not star_known and not star_presence(region_type, rng):
        return {"sector": sector, "hex": hex_, "empty": True,
                "generated": True, "region_type": region_type}

    stars = gen_stars(rng)
    sdi = gen_sdi(rng)
    density, bodies_dice = tables.lookup_band(tables.SYSTEM_DENSITY, min(sdi, 22))
    n_bodies = roll(bodies_dice, rng) if bodies_dice != "0" else 0
    bodies = gen_specific_bodies(sdi, rng)
    habitable = bool(bodies.get("habitable") or bodies.get("borderline_habitable"))
    uwp = gen_mainworld_uwp(rng, habitable) if n_bodies else None
    bodies_detail = gen_bodies_detail(rng, n_bodies, bodies, habitable)

    return {
        "sector": sector,
        "hex": hex_,
        "empty": False,
        "generated": True,
        "region_type": region_type,
        "stars": stars,
        "sdi": sdi,                      # B3 p.20-21
        "density": density,              # B3 p.8
        "planetary_bodies": n_bodies,
        "gas_giant": bodies["gas_giant_refuel"],       # None = niepewne
        "planetoids": bodies["planetoids_mining"],
        "borderline_habitable": bodies["borderline_habitable"],
        "habitable": bodies["habitable"],
        "bodies_detail": bodies_detail,
        "mainworld_uwp": uwp,
        # --- warstwa GM (filtrowana w API graczy) ---
        "gm_notes": "",
        "gm_encounter": None,
        "gm_override": {},
    }


def canonical_system(sector: str, hex_: str, world: dict) -> dict:
    """Rekord dla systemu kanonicznego z dotmapy (pelny UWP)."""
    return {
        "sector": sector,
        "hex": hex_,
        "empty": False,
        "generated": False,
        "canon": True,
        "name": world.get("name") or None,
        "stars": (world.get("stellar") or "").split("  ") if world.get("stellar") else [],
        "mainworld_uwp": world.get("uwp"),
        "bases": world.get("bases", ""),
        "zone": world.get("zone", ""),
        "remarks": world.get("remarks", ""),
        # PBG z danych kanonicznych: liczba GG znana -> tankowanie pewne
        "gas_giant": (world["gg"] > 0) if world.get("gg") is not None else None,
        "gm_notes": "",
        "gm_encounter": None,
        "gm_override": {},
    }
