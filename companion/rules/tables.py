"""Tabele i stale B3/B2 jako dane. Kazda stala cytuje strone druku.

Zrodlo prawdy: companion/docs/rules-spec.md.
Wpisy oznaczone `# HR:` to house-rules na bledy druku (spec §13).
"""

# --- STATEK (B2 karta statku + core MGT2; spec §0) ---
SHIP = {
    "hull_tons": 75_000,          # B3 p.68 (750 t = 1%/pass)
    "jump_rating": 4,             # B2 karta
    "thrust": 4,                  # B2 karta
    "fuel_tank_tons": 27_900,     # B2 karta: "8 weeks of operation, J-4"
    "fuel_per_parsec": 6_750,     # core 10%/pc * 75000 * 0.9 (J-drive -10%, B2)
    "powerplant_fuel_tons": 900,  # wyliczenie: 27900 - 27000 (spec §0)
    "powerplant_tons_per_week": 112.5,
    "fuel_processor_tons_per_day": 4_000,  # B2 karta
    "skim_tons_per_pass_deep": 750,    # B3 p.68, Pilot DM-2
    "skim_tons_per_pass_safe": 375,    # B3 p.68, gorne warstwy
    "crew_complement": 488,       # B2 (ustalenie briefow; B3 p.37 "just under 500")
    "supply_capacity": 200_000,   # B3 p.46
    "supply_per_day": 1_000,      # B3 p.46
    "starting_cei": 7,            # B2 (Crew Effectiveness Index "set at a value of 7")
    "starting_ceim": 0,           # B2
}

# --- SURVEY INDEX (B3 p.71) ---
# SI -> co jest ujawnione graczom (klucze uzywane przez filtr widoku)
SI_REVEALS = {
    0: [],
    1: ["star_presence", "major_phenomena"],
    2: ["star_class_general"],
    3: ["star_types"],
    4: ["brown_dwarfs"],
    5: ["gas_giants"],
    6: ["terrestrials", "belts"],
    7: ["atmosphere_presence", "surface_water"],
    8: ["uwp_estimate_shs"],       # szacunek Size/Hydro/Atmo
    9: ["uwp_correct_shs", "pop_tl_estimate"],
    10: ["uwp_full"],
    11: ["rogue_planets"],
    12: ["rogue_comets"],
}
SI_MAX = 12

# Tryby sweepu systemu (B3 p.72-74): (czas: kosc, jednostka), przyrost SI, flagi
SURVEY_MODES = {
    # remote: Average(8+) DEI/Electronics; SI += 2*Effect (B3 p.72)
    "remote": {"time": ("2D", "min"), "si_gain": "2xEffect", "reveals_ship": False,
               "check": ("Average", 8), "page": "B3 p.72"},
    "passive": {"time": ("2D", "min"), "si_gain": "+1", "reveals_ship": False,
                "page": "B3 p.73"},
    "active": {"time": ("2D", "h"), "si_gain": "+D3", "reveals_ship": True,
               "page": "B3 p.73"},
    "full": {"time": ("4D", "h"), "si_gain": "+1D", "reveals_ship": False,
             "requires_movement": True, "page": "B3 p.74"},
    # pobyt w systemie: +1 co 1D dni (B3 p.74) - obslugiwane przez uplyw czasu
}

SCAN_POINTS_PER_DAY = 6  # B3 p.72, p.74

# Deep space: prog scan-points na detekcje typu ciala, +1/parsek odleglosci (B3 p.74)
DEEP_SPACE_DETECTION = {
    "star": 0,           # automatycznie
    "brown_dwarf": 4,
    "large_gas_giant": 6,
    "small_gas_giant": 8,
    "planetary_body": 10,
    "cometary_body": 12,
}

# Short-Range Detection po skoku w pusty hex (B3 p.75): 2D + DM
SHORT_RANGE_DM = {
    "known_interstellar_object": 2,
    "same_hex_as_system": 4,
    "oort_cloud": 6,
    "kuiper_belt": 8,
    "per_parsec_to_nearest_system": -1,
}
# wynik 2D -> liczba obiektow ("1D3"/"1D" = rzut)
SHORT_RANGE_RESULTS = [
    ((2, 7), 0), ((8, 9), 1), ((10, 11), "1D3"), ((12, 99), "1D_plus_over12"),
]
SHORT_RANGE_SWEEP_DAYS = "1D"  # sfera ~50 AU (B3 p.75)

# Nature of Objects Found (B3 p.76): 2D -> wynik; 2 i 12 maja podtabele 1D
NATURE_OF_OBJECTS = {
    2: ("subtable_unusual", None),
    (3, 4): ("glitch", "Sensor glitch - nic nie ma"),
    (5, 9): ("small_comet", "Mala kometa lodowa - JEDNO tankowanie"),
    (10, 11): ("cometary_body", "Cialo kometarne - WIELE tankowan"),
    12: ("subtable_large", None),
}
NATURE_SUB_2 = {1: "Extremely unusual object", 2: "Drifting interstellar wreck",
                3: "Dangerous object", 4: "Anomalia grawitacyjna/radiacyjna",
                5: "Planetoida ze sladami zamieszkania", 6: "Niezwykle gesty oblok gazu"}
NATURE_SUB_12 = {1: "Large Cometary Body", 2: "Rogue Dwarf Planet",
                 3: "Rogue Planetoid Cluster", 4: "Rogue Planet",
                 5: "Rogue Gas Giant", 6: "Highly unusual large rogue body"}

# --- SKOK (B3 p.10-11, p.17; core MGT2) ---
JUMP_TIME_HOURS = 168  # "usual 7 days" (B3 p.17); core: 148+6D h
JUMP_ENV_DM = {
    "into_or_from_nebula": -4,     # B3 p.11
    "through_nebula": -2,
    "through_protostar_cloud": -4,
    "into_or_from_protostar_cloud": -8,
}

# --- TANKOWANIE (B3 p.68-69) ---
SKIM_PASS_TIME = ("2D", "min")     # B3 p.68
SKIM_DEEP_PILOT_DM = -2            # B3 p.68
# Fuel Source check per gestosc systemu: (trudnosc, prog, czas kosc, jednostka)
FUEL_SOURCE_CHECK = {
    "extremely_dense": ("Simple", 2, "1D", "h"),
    "very_dense": ("Easy", 4, "2D", "h"),
    "dense": ("Routine", 6, "3D", "h"),
    "normal": ("Average", 8, "4D", "h"),
    "sparse": ("Difficult", 10, "6D", "h"),
    "very_sparse": ("Very Difficult", 12, "8D", "h"),
    "extremely_sparse": ("Formidable", 14, "12D", "h"),
    "barren": ("Special", None, None, None),  # jak deep space objects (B3 p.69)
}

# --- GENERACJA SYSTEMOW (B3 p.8, p.20-21) ---
# Star System Presence (B3 p.20): typ regionu -> (prog, kosci) "wynik <= prog na kosci"
STAR_PRESENCE = {
    "cluster": (5, "1D"),
    "dense": (4, "1D"),
    "average": (3, "1D"),
    "sparse": (2, "1D"),
    "rift": (2, "2D"),
    "void": (3, "3D"),
}

# SDI -> (kategoria, kosc liczby cial) (B3 p.8)
SYSTEM_DENSITY = [
    ((0, 0), "barren", "0"),
    ((1, 3), "extremely_sparse", "1"),
    ((4, 6), "very_sparse", "D3"),
    ((7, 9), "sparse", "1D+1"),
    ((10, 12), "normal", "2D"),
    ((13, 15), "dense", "2D+3"),
    ((16, 18), "very_dense", "3D"),
    ((19, 21), "extremely_dense", "4D"),
    ((22, 99), "anomalous", "4D"),
]

# Specific Bodies (B3 p.21): 1D + przydzielony DM z puli SDI, prog per cialo
SPECIFIC_BODIES = {
    "gas_giant_refuel": 9,
    "borderline_habitable": 9,
    "habitable": 12,
    "planetoids_mining": 10,
}

# --- RATE OF ADVANCE (B3 p.17) ---
# rate -> (avoid_event prog, poi prog, parseki kosc)
RATE_OF_ADVANCE = {
    "flank": (10, 12, "1D+6"),
    "rapid": (8, 10, "1D+4"),   # HR: druk "18+", poprawione na 8+ (spec §13)
    "cursory": (6, 8, "1D+2"),
    "detailed": (4, 6, "1D"),
}

EVENTS_2D = {
    2: "Major Supply Problem", 3: "Major Crew Problem", 4: "Bad Data",
    5: "Cargo Problem", 6: "Minor Crew Problem", 7: "Minor Supply Problem",
    8: "Crewmember Taken Ill", 9: "Non-Critical System Malfunction",
    10: "Critical System Malfunction", 11: "Non-Critical System Breakdown",
    12: "Critical System Breakdown",
}
SUPPLY_LOSS = {"minor": "1Dx5%", "major": "3Dx5%"}  # B3 p.18

# --- SUPPLY (B3 p.46-49) ---
# progi budzetu dziennego (% normy) -> (check lub auto, prog/kosc, maintenance DM)
SUPPLY_LEVEL_EFFECTS = [
    ((0, 0), ("auto", "-1D", "2D"), 12),
    ((1, 10), ("auto", "-D3", "2D"), 10),
    ((11, 20), ("auto", "-1", "2D"), 8),
    ((21, 40), ("check", 14, "4D"), 6),
    ((41, 60), ("check", 12, "4D"), 4),
    ((61, 80), ("check", 10, "4D"), 2),
    ((81, 90), ("check", 8, "4D"), 1),
    ((91, 100), ("check", 6, "4D"), 0),
]

# --- MAINTENANCE (B3 p.53) ---
# wynik 2D+DM -> (defects, breakdowns, failures); "ALL"/"X" specjalne
MAINTENANCE_ISSUES = [
    ((-99, 3), (0, 0, 0)),
    ((4, 6), (1, 0, 0)),
    ((7, 9), (2, 0, 0)),
    ((10, 12), (3, 0, 0)),
    ((13, 15), (1, 1, 0)),
    ((16, 20), (2, 1, 0)),  # HR: druk konczy na 18, brak wiersza 19-20 -> jak 16-18 (spec §13)
    ((21, 24), (3, 1, 0)),
    ((25, 27), (1, 2, 1)),
    ((28, 30), (2, 2, 1)),
    ((31, 33), (3, 2, 1)),
    ((34, 36), (1, 3, 2)),
    ((37, 39), (2, 3, 2)),
    ((40, 42), ("ALL", 3, 2)),
    ((43, 44), ("ALL", "ALL", 2)),   # HR: druk "43-45" i "45+" nachodza na 45 -> 45 idzie wyzej
    ((45, 999), ("ALL", "ALL", "ALL")),
]
OFFSET_COST = {"defect": 1, "breakdown": 3, "failure": 6}  # B3 p.53

# --- CEI (B3 p.32): CEI -> task DM ---
CEI_DM = {0: -6, 1: -5, 2: -4, 3: -3, 4: -2, 5: -1, 6: -1, 7: 0, 8: 0,
          9: 1, 10: 1, 11: 2, 12: 3, 13: 4, 14: 5, 15: 6}

# CEIM Changes co 2D tygodni (B3 p.34): 2D+Effect -> (mor_delta, ceim_delta)
CEIM_CHANGES = [
    ((-99, 0), ("-1D+3", -3)),
    ((1, 2), ("-1D", -2)),
    ((3, 4), ("-D3", -1)),
    ((5, 8), (None, 0)),
    ((9, 11), ("+1", 0)),
    ((12, 99), ("+D3", 1)),
]

# --- CFI (B3 p.41-42) ---
FATIGUE_INTERVALS = {
    "initial": "10D", "standard": "6D", "stressful": "4D", "highly_stressful": "2D",
}
FATIGUE_LEVELS = [  # (nazwa, DM, kara MOR przy wejsciu)
    ("fatigued", 0, None),          # HR: kolumna DM rozjechana w druku (spec §13)
    ("highly_fatigued", -1, None),
    ("dangerously_fatigued", -2, "-1"),
    ("exhausted", -3, "-D3"),
    ("incapable", -4, "-1D"),
]

# --- TRANZYTY W SYSTEMIE (B3 p.64) ---
IN_SYSTEM_TRANSITS_H = {
    "body_to_satellite": (1, 2),
    "short_inner": (20, 24),
    "longer_inner": (30, 40),
    "mainworld_to_inner_edge": (50, 60),
    "mainworld_to_gg": (60, 80),
    "mainworld_to_far_outsystem": (250, 300),
    "outsystem_close": (350, 400),
    "outsystem_opposite": (500, 600),
}


def lookup_band(table, value):
    """Zwraca wpis z tabeli pasm [((lo,hi), ...), ...] dla wartosci."""
    for band, *rest in table:
        lo, hi = band
        if lo <= value <= hi:
            return rest[0] if len(rest) == 1 else tuple(rest)
    raise ValueError(f"wartosc {value} poza tabela")
