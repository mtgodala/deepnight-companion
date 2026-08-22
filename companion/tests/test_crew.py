"""Testy drzewa zalogi: szablon B2 s.42-45 + API /api/crew (filtr gm_*, tryb GM)."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / "companion" / "data" / "crew_template.json"


def _nodes() -> list[dict]:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))["nodes"]


# ------------------------------------------------------------ szablon (kanon)

def test_template_division_sums():
    """Etaty dywizji wg B2 s.44-45 (atrybut division); suma = 488 (B2 s.45)."""
    nodes = _nodes()
    expected = {"command": 12, "flight": 57, "engineering": 195,
                "operations": 132, "mission": 92}
    sums: dict[str, int] = {}
    for n in nodes:
        sums[n["division"]] = sums.get(n["division"], 0) + (n["count"] or 0)
    assert sums == expected
    assert sum(sums.values()) == 488


def test_template_integrity():
    nodes = _nodes()
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids)), "zduplikowane id"
    idset = set(ids)
    for n in nodes:
        assert n["parent"] is None or n["parent"] in idset, n["id"]
        # wezel jest albo stanowiskiem (count), albo grupa (count=None)
        assert n["count"] is None or n["count"] >= 1
    # lancuch dowodzenia: dokladnie jeden korzen (Dowodca Misji)
    roots = [n for n in nodes if n["parent"] is None]
    assert [r["id"] for r in roots] == ["mission-commander"]


# ------------------------------------------------------------------ API crew

@pytest.fixture()
def crew_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPNIGHT_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("DEEPNIGHT_GM_TOKEN_FILE", str(tmp_path / "gm_token.txt"))
    from companion import server
    importlib.reload(server)
    # minimalny ship.json — log_event/undo czytaja date; reszta niepotrzebna
    (tmp_path / "ship.json").write_text(json.dumps({
        "position": {"sector": "Test", "hex": "0101"},
        "date_imperial": "001-1105",
    }), encoding="utf-8")
    from fastapi.testclient import TestClient
    client = TestClient(server.app)
    with client:   # odpala startup (load_sectors + gm_token)
        yield client, server


def _gm_headers(server) -> dict:
    return {"X-GM-Token": server.gm_token()}


def _add_person(client, server, **over) -> dict:
    body = {"slug": "kasia-vorek", "name": "Kasia Vorek", "node": "cfo",
            "kind": "npc", "status": "alive", "note": "notka jawna",
            "gm_note": "SEKRET", **over}
    return client.post("/api/crew/person", json=body, headers=_gm_headers(server))


def test_crew_get_player_view_hides_gm_fields(crew_app):
    client, server = crew_app
    assert _add_person(client, server).status_code == 200
    r = client.get("/api/crew").json()
    assert r["gm"] is False
    assert len(r["people"]) == 1
    assert "gm_note" not in r["people"][0]
    assert r["people"][0]["note"] == "notka jawna"
    # tryb GM widzi wszystko
    g = client.get("/api/crew", headers=_gm_headers(server)).json()
    assert g["gm"] is True and g["people"][0]["gm_note"] == "SEKRET"


def test_crew_post_open_at_table_but_gm_fields_guarded(crew_app):
    """Wpis nazwiska otwarty przy stole; gm_note i delete tylko dla GM."""
    client, server = crew_app
    # dodanie bez tokenu dziala, ale gm_note jest ignorowane
    r = client.post("/api/crew/person", json={
        "slug": "x", "name": "X", "node": "cfo", "gm_note": "przemyt"})
    assert r.status_code == 200
    g = client.get("/api/crew", headers=_gm_headers(server)).json()
    assert g["people"][0]["gm_note"] == ""
    # GM ustawia gm_note; update bez tokenu jej NIE nadpisuje
    _add_person(client, server, slug="x", name="X", node="cfo")
    client.post("/api/crew/person", json={
        "slug": "x", "name": "X", "node": "cfo", "gm_note": "proba nadpisania"})
    g = client.get("/api/crew", headers=_gm_headers(server)).json()
    assert g["people"][0]["gm_note"] == "SEKRET"
    # delete bez tokenu zabronione
    d = client.post("/api/crew/person", json={"slug": "x", "delete": True})
    assert d.status_code == 403


def test_crew_assign_to_group_node(crew_app):
    """Nazwisko mozna wpisac takze na wezle zespolu (np. team-bridge)."""
    client, server = crew_app
    r = _add_person(client, server, slug="og", name="Ogden", node="team-bridge")
    assert r.status_code == 200
    people = client.get("/api/crew").json()["people"]
    assert people[0]["node"] == "team-bridge"


def test_crew_post_validates_node_and_status(crew_app):
    client, server = crew_app
    assert _add_person(client, server, node="nie-ma-takiego").status_code == 422
    assert _add_person(client, server, status="zombie").status_code == 422


def test_crew_upsert_and_delete(crew_app):
    client, server = crew_app
    _add_person(client, server)
    _add_person(client, server, status="wounded")          # update po slugu
    r = client.get("/api/crew", headers=_gm_headers(server)).json()
    assert len(r["people"]) == 1 and r["people"][0]["status"] == "wounded"
    d = client.post("/api/crew/person", json={"slug": "kasia-vorek", "delete": True},
                    headers=_gm_headers(server))
    assert d.status_code == 200
    assert client.get("/api/crew").json()["people"] == []


def test_crew_journal_gm_only_filter(crew_app):
    client, server = crew_app
    _add_person(client, server, log_gm_only=True)
    player_rows = client.get("/api/journal").json()
    assert all(row["kind"] != "crew" for row in player_rows)
    gm_rows = client.get("/api/journal", headers=_gm_headers(server)).json()
    crew_rows = [row for row in gm_rows if row["kind"] == "crew"]
    assert crew_rows and crew_rows[0]["gm_only"] is True


def test_crew_undo_restores_people(crew_app):
    client, server = crew_app
    _add_person(client, server)
    assert len(client.get("/api/crew").json()["people"]) == 1
    u = client.post("/api/undo")
    assert u.status_code == 200 and u.json()["undone"] == "crew"
    assert client.get("/api/crew").json()["people"] == []
