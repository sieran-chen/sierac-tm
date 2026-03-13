"""API endpoint tests: summary, telemetry, alarms, 404 for unknown equipment."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_summary_endpoint() -> None:
    r = client.get("/api/twin/equipment/roller-001/summary")
    assert r.status_code == 200
    data = r.json()
    assert "equipment" in data
    assert data["equipment"]["id"] == "roller-001"
    assert data["equipment"]["name"] == "1号滚筒剔除装置"
    assert "highlights" in data
    assert "roller_speed" in data["highlights"]
    assert "active_alarms" in data
    assert "updated_at" in data


def test_telemetry_endpoint() -> None:
    r = client.get("/api/twin/equipment/roller-001/telemetry")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    point_ids = {t["point_id"] for t in data}
    assert "roller_speed" in point_ids
    assert "temperature" in point_ids
    assert "oee" in point_ids


def test_alarms_endpoint() -> None:
    r = client.get("/api/twin/equipment/roller-001/alarms?active=true")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_unknown_equipment_404() -> None:
    r = client.get("/api/twin/equipment/unknown-99/summary")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_history_endpoint() -> None:
    r = client.get(
        "/api/twin/equipment/roller-001/history?point_id=roller_speed&hours=4&interval=10"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["point_id"] == "roller_speed"
    assert "point_name" in data
    assert "unit" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_history_unknown_equipment_404() -> None:
    r = client.get(
        "/api/twin/equipment/unknown-99/history?point_id=speed&hours=4"
    )
    assert r.status_code == 404


def test_history_unknown_point_returns_empty_data() -> None:
    r = client.get(
        "/api/twin/equipment/roller-001/history?point_id=nonexistent_point&hours=4"
    )
    assert r.status_code == 200
    assert r.json()["point_id"] == "nonexistent_point"
    assert r.json()["data"] == []


def test_viewer_path_config_default(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "viewer-calibration.json"
    monkeypatch.setenv("TWIN_VIEWER_CONFIG_PATH", str(config_path))

    r = client.get("/api/twin/equipment/roller-001/viewer-path-config")
    assert r.status_code == 200
    data = r.json()
    assert data["start"]["front"] == -8
    assert data["start"]["right"] == 8.5
    assert data["waypoint"] is None
    assert data["end"]["right"] == -8.5


def test_viewer_path_config_save_and_reload(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "viewer-calibration.json"
    monkeypatch.setenv("TWIN_VIEWER_CONFIG_PATH", str(config_path))

    payload = {
        "start": {"x": -8, "z": 8.5, "front": -8, "up": 0, "right": 8.5},
        "waypoint": {"x": -2, "z": 1.5, "front": -2, "up": 0, "right": 1.5},
        "end": {"x": -8.46, "z": -0.74, "front": 0, "up": 0, "right": -8.5},
    }

    put_response = client.put(
        "/api/twin/equipment/roller-001/viewer-path-config",
        json=payload,
    )
    assert put_response.status_code == 200
    assert put_response.json() == payload

    saved_file = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_file["roller-001"]["waypoint"]["front"] == -2

    get_response = client.get("/api/twin/equipment/roller-001/viewer-path-config")
    assert get_response.status_code == 200
    assert get_response.json() == payload
