"""Testy silnika przeciw spec (companion/docs/rules-spec.md)."""

import random

import pytest

from companion.rules import dice, jump, survey, sysgen, tables


# --- kosci ---

def test_roll_notation():
    rng = random.Random(1)
    assert 2 <= dice.roll("2D", rng) <= 12
    assert 1 <= dice.roll("D3", rng) <= 3
    assert 5 <= dice.roll("1D+4", rng) <= 10
    assert dice.roll("2Dx5", rng) % 5 == 0
    assert 0 <= dice.roll("3D-3", rng) <= 15


def test_seeded_rng_deterministic():
    a = dice.seeded_rng("sysgen", "Deepnight", "0101")
    b = dice.seeded_rng("sysgen", "Deepnight", "0101")
    assert [a.randint(1, 6) for _ in range(10)] == [b.randint(1, 6) for _ in range(10)]


# --- statek / paliwo (spec §0) ---

def test_ship_fuel_math():
    s = tables.SHIP
    assert s["fuel_per_parsec"] == 6750          # 10% * 75000 * 0.9
    assert s["jump_rating"] * s["fuel_per_parsec"] == 27000   # pelny J-4
    assert s["fuel_tank_tons"] - 27000 == 900    # reszta = reaktor ~8 tyg.


def test_plan_jump_j4_fuel():
    origin = jump.hex_to_world(-1, -1, "0211")   # Giikur
    dest = jump.hex_to_world(-2, -1, "3010")     # Habretic, 4 pc (B2: "4 parsecs")
    plan = jump.plan_jump(origin, dest, fuel_on_board=27900)
    assert plan.parsecs == 4
    assert plan.fuel_required == 27000
    assert plan.fuel_ok and plan.range_ok
    assert plan.time_hours == 168


def test_plan_jump_out_of_range_and_fuel():
    origin = jump.hex_to_world(-1, -1, "0211")
    dest = jump.hex_to_world(-1, -1, "0610")     # 4 pc (z API)
    plan = jump.plan_jump(origin, dest, fuel_on_board=1000)
    assert plan.parsecs == 4 and not plan.fuel_ok
    far = jump.hex_to_world(-1, -1, "1011")      # >4 pc
    assert not jump.plan_jump(origin, far, 30000).range_ok


# --- odleglosci hex: ground truth z /api/jumpworlds (Giikur 0211) ---

GIIKUR = (-1, -1, "0211")
API_DISTANCES = [
    ((-1, -1, "0311"), 1), ((-1, -1, "0210"), 1),
    ((-1, -1, "0209"), 2), ((-1, -1, "0110"), 2),
    ((-1, -1, "0109"), 3), ((-2, -1, "3209"), 3),
    ((-1, -1, "0610"), 4), ((-2, -1, "3208"), 4),
    ((-1, -1, "0408"), 4), ((-2, -1, "3010"), 4),
]


@pytest.mark.parametrize("target,expected", API_DISTANCES)
def test_hex_distance_vs_travellermap(target, expected):
    a = jump.hex_to_world(*GIIKUR[:2], GIIKUR[2])
    b = jump.hex_to_world(*target[:2], target[2])
    assert jump.distance_pc(a, b) == expected
    assert jump.distance_pc(b, a) == expected  # symetria


# --- skimming (B3 p.68 + B2 procesor) ---

def test_skim_full_j4_refuel():
    plan = jump.plan_skim(27000, mode="deep", rng=random.Random(7))
    assert plan.passes == 36                      # 27000 / 750
    assert plan.tons_skimmed == 27000
    assert plan.pilot_dm == -2
    assert 6.5 <= plan.processing_days <= 7.0     # 4000 t/dzien
    safe = jump.plan_skim(27000, mode="safe", rng=random.Random(7))
    assert safe.passes == 72 and safe.pilot_dm == 0


def test_skim_processor_defects_slowdown():
    # 4000 t -> 6 passow x 750 = 4500 t; 4500/4000 dnia * 1.2 (2 Defekty, B3 p.55)
    b = jump.plan_skim(4000, rng=random.Random(1), processor_defects=2)
    assert b.tons_skimmed == 4500
    assert b.processing_days == pytest.approx(4500 / 4000 * 1.2, abs=0.01)


# --- Survey Index (B3 p.71-74) ---

def test_si_reveals_progression():
    assert "star_presence" in survey.revealed_keys(1)
    assert "gas_giants" not in survey.revealed_keys(4)
    assert "gas_giants" in survey.revealed_keys(5)
    assert "uwp_full" in survey.revealed_keys(10)
    assert survey.revealed_keys(0) == []


def test_sweep_largest_increase_rule():
    # B3 p.73: Active dal +2, potem Full +4 -> lacznie +4, nie +6
    res = survey.apply_sweep(si=5, mode="full", best_sweep_gain=2,
                             rng=random.Random(3))
    base = 5 - 2
    expected = base + max(res.gain, 2)
    assert res.si_after == min(12, expected)
    if res.gain <= 2:
        assert not res.applied and res.si_after == 5


def test_sweep_passive_plus_one_and_cap():
    res = survey.apply_sweep(si=12, mode="passive")
    assert res.si_after == 12                     # cap SI_MAX
    res2 = survey.apply_sweep(si=3, mode="passive")
    assert res2.si_after == 4 and not res2.reveals_ship


def test_sweep_active_reveals_ship():
    res = survey.apply_sweep(si=1, mode="active", rng=random.Random(2))
    assert res.reveals_ship                       # B3 p.73
    assert 1 <= res.gain <= 3


def test_sweep_remote_uses_effect():
    res = survey.apply_sweep(si=2, mode="remote", effect=3)
    assert res.gain == 6 and res.si_after == 8    # SI += 2*Effect (B3 p.72)
    with pytest.raises(ValueError):
        survey.apply_sweep(si=2, mode="remote")


def test_deep_space_threshold():
    # przyklad z ksiazki (B3 p.75): brown dwarf 4 pc dalej = 8
    assert survey.deep_space_threshold("brown_dwarf", 4) == 8
    assert survey.deep_space_threshold("cometary_body", 4) == 16


def test_short_range_detection_bands():
    out = survey.short_range_detection(["kuiper_belt"], 0, rng=random.Random(5))
    assert out["dm"] == 8
    assert out["count"] >= 0 and out["sweep_days"] >= 1
    assert len(out["objects"]) == out["count"]


# --- generacja systemow (B3 p.8, p.20-21) ---

def test_generate_system_deterministic():
    a = sysgen.generate_system("Deepnight", "1520")
    b = sysgen.generate_system("Deepnight", "1520")
    assert a == b
    c = sysgen.generate_system("Deepnight", "1521")
    assert c != a


def test_sdi_ranges():
    rng = random.Random(11)
    values = [sysgen.gen_sdi(rng) for _ in range(2000)]
    assert min(values) >= 0 and max(values) <= 30  # B3 p.21
    assert 7 <= sorted(values)[len(values) // 2] <= 12  # typowo 8-11


def test_density_bands():
    assert tables.lookup_band(tables.SYSTEM_DENSITY, 0)[0] == "barren"
    assert tables.lookup_band(tables.SYSTEM_DENSITY, 10)[0] == "normal"
    assert tables.lookup_band(tables.SYSTEM_DENSITY, 22)[0] == "anomalous"


def test_star_presence_rift_rare():
    rng = random.Random(42)
    hits = sum(sysgen.star_presence("rift", rng) for _ in range(3000))
    # Rift: 2 na 2D = 1/36 ~ 2.8%
    assert 0.01 < hits / 3000 < 0.06


def test_generated_uwp_uninhabited():
    sys_ = sysgen.generate_system("Voidshore One", "0505")
    if not sys_["empty"] and sys_["mainworld_uwp"]:
        uwp = sys_["mainworld_uwp"]
        assert uwp[0] in ("X", "E")               # HR spec §6
        assert uwp[4:7] == "000" and uwp.endswith("-0")


def test_canonical_overrides_generator():
    world = {"name": "Demnan", "uwp": "E567000-0", "stellar": "F2 V K2 V G2 V",
             "bases": "NS", "zone": "", "remarks": "Ba"}
    rec = sysgen.canonical_system("Incognita Citerior", "3124", world)
    assert rec["canon"] and not rec["generated"]
    assert rec["mainworld_uwp"] == "E567000-0"


# --- tabele HR (spec §13) ---

def test_maintenance_issues_hr_19_20():
    assert tables.lookup_band(tables.MAINTENANCE_ISSUES, 19) == (2, 1, 0)
    assert tables.lookup_band(tables.MAINTENANCE_ISSUES, 20) == (2, 1, 0)
    assert tables.lookup_band(tables.MAINTENANCE_ISSUES, 45) == ("ALL", "ALL", "ALL")
    assert tables.lookup_band(tables.MAINTENANCE_ISSUES, 2) == (0, 0, 0)


def test_rate_of_advance_hr_rapid():
    assert tables.RATE_OF_ADVANCE["rapid"][0] == 8  # HR: druk mial "18+"


def test_supply_level_bands():
    assert tables.lookup_band(tables.SUPPLY_LEVEL_EFFECTS, 50)[1] == 4   # przyklad B3 p.49
    assert tables.lookup_band(tables.SUPPLY_LEVEL_EFFECTS, 100)[1] == 0
    assert tables.lookup_band(tables.SUPPLY_LEVEL_EFFECTS, 0)[0][0] == "auto"


def test_cei_dm_table():
    assert tables.CEI_DM[7] == 0 and tables.CEI_DM[0] == -6 and tables.CEI_DM[15] == 6


# --- checki silnika (checks.py) ---

from companion.rules import checks


def test_cei_dm_clamp():
    assert checks.cei_dm(7) == 0 and checks.cei_dm(-3) == -6 and checks.cei_dm(20) == 6


def test_remote_sweep_check_modifiers():
    ship = {"cei": 7, "ceim": 0, "dei": {"mission": 9}}
    c = checks.remote_sweep_check(ship, rng=random.Random(1))
    labels = [l for l, _ in [(d["label"], d["value"]) for d in c.as_dict()["dms"]]]
    assert any("suite" in l for l in labels)          # DM+2 (B3 p.72)
    assert any("DEI" in l or "ECEI" in l for l in labels)
    # DEI Mission 9 (+1) > ECEI 7 (0) -> uzyty wiekszy (B3 p.34)
    assert sum(v for _, v in c.dms) == 3              # +1 (DEI 9) +2 (suite)
    assert c.total == sum(c.dice) + 3
    assert c.effect == c.total - 8


def test_skim_check_deep_dm():
    ship = {"cei": 7, "ceim": 0, "dei": {"flight": 7}}
    c = checks.skim_check(ship, "deep", rng=random.Random(2))
    assert ("głębokie warstwy atmosfery", -2) in c.dms
    safe = checks.skim_check(ship, "safe", rng=random.Random(2))
    assert all(v != -2 for _, v in safe.dms)


def test_post_jump_check_easy():
    ship = {"cei": 7, "ceim": 0, "dei": {}}
    c = checks.post_jump_check(ship, rng=random.Random(3))
    assert c.target == 4                              # Easy (B3 p.63)


# --- lista cial (bodies_detail) ---

def test_bodies_detail_deterministic_and_gg():
    a = sysgen.generate_system("Deepnight", "0808")
    b = sysgen.generate_system("Deepnight", "0808")
    assert a == b
    if not a["empty"]:
        assert "bodies_detail" in a
        zones = {"wewnętrzna", "ekosfera", "zewnętrzna", "daleka"}
        assert all(x["zone"] in zones for x in a["bodies_detail"])
        if a["gas_giant"]:
            assert any(x["kind"] == "gg" for x in a["bodies_detail"])


# --- audyt 2026-08-08: remote sweep i tankowanie z lodu ---

def test_remote_sweep_costs_days_and_cumulates():
    """Remote: koszt 2D scan points => czas w dniach (B3 p.72+74);
    NIE podlega largest-increase (p.73 dotyczy passive/active/full)."""
    r = survey.apply_sweep(3, "remote", effect=2, rng=random.Random(1))
    assert r.time_unit == "d"
    assert 1 <= r.time_amount <= 2                    # ceil(2D/6)
    assert 2 <= r.dice_log["scan_points"] <= 12
    assert r.si_after == 3 + 4                        # 2*Effect, kumulacja od SI
    assert r.applied


def test_remote_sweep_failed_check_no_gain():
    r = survey.apply_sweep(5, "remote", effect=0, rng=random.Random(1))
    assert r.si_after == 5 and not r.applied


def test_insystem_surveys_keep_largest_increase():
    """Passive po sweepie +3 nie podnosi SI (largest increase, B3 p.73)."""
    r = survey.apply_sweep(6, "passive", best_sweep_gain=3, rng=random.Random(1))
    assert r.si_after == 6 and not r.applied


def test_ice_refuel_check_flight_division():
    ship = {"cei": 7, "ceim": 0, "dei": {"flight": 7}}
    c = checks.ice_refuel_check(ship, rng=random.Random(4))
    assert c.target == 8
    assert c.page == "B3 p.70"
