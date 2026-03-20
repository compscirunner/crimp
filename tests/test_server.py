"""Tests for the crimp serve FastAPI app."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crimp.manifest import load
from crimp.server import create_app

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def client(scout):
    app = create_app(scout)
    return TestClient(app)


class TestIndexPage:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_contains_project_name(self, client, scout):
        r = client.get("/")
        assert scout.project.name in r.text

    def test_contains_all_connection_ids(self, client, scout):
        r = client.get("/")
        for conn in scout.connections:
            assert conn.id in r.text, f"{conn.id} missing from index"

    def test_contains_htmx(self, client):
        r = client.get("/")
        assert "htmx.org" in r.text

    def test_contains_phase_headings(self, client):
        r = client.get("/")
        assert "Phase 1" in r.text
        assert "Phase 2" in r.text

    def test_contains_pass_buttons(self, client):
        r = client.get("/")
        assert "Pass" in r.text
        assert "Fail" in r.text


class TestStepActions:
    def test_mark_pass(self, client, scout):
        conn_id = scout.connections[0].id
        r = client.post(f"/step/{conn_id}/pass")
        assert r.status_code == 200
        assert "pass" in r.text

    def test_mark_fail(self, client, scout):
        conn_id = scout.connections[1].id
        r = client.post(f"/step/{conn_id}/fail")
        assert r.status_code == 200
        assert "fail" in r.text

    def test_mark_skip(self, client, scout):
        conn_id = scout.connections[2].id
        r = client.post(f"/step/{conn_id}/skip")
        assert r.status_code == 200
        assert "skip" in r.text

    def test_reset(self, client, scout):
        conn_id = scout.connections[0].id
        client.post(f"/step/{conn_id}/pass")
        r = client.post(f"/step/{conn_id}/reset")
        assert r.status_code == 200

    def test_invalid_action(self, client, scout):
        conn_id = scout.connections[0].id
        r = client.post(f"/step/{conn_id}/explode")
        assert r.status_code == 400

    def test_unknown_conn(self, client):
        r = client.post("/step/not_a_real_conn/pass")
        assert r.status_code == 404


class TestSummaryEndpoint:
    def test_summary_returns_json(self, client):
        r = client.get("/summary")
        assert r.status_code == 200
        data = r.json()
        assert "passed" in data
        assert "failed" in data
        assert "skipped" in data
        assert "total" in data
        assert "pct" in data

    def test_summary_total_matches_connections(self, client, scout):
        r = client.get("/summary")
        data = r.json()
        assert data["total"] == len(scout.connections)

    def test_summary_pct_in_range(self, client):
        r = client.get("/summary")
        data = r.json()
        assert 0 <= data["pct"] <= 100
