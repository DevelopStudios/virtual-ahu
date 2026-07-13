# virtual-ahu/tests/test_api.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.objects import router as objects_router
from app.bacnet import points
from app.bacnet.registry import Registry
from app.main import create_app


@pytest.fixture
def client():
    """Router mounted on a bare app, singleton registry freshly populated.

    No lifespan/sim here — these tests exercise ReadProperty/WriteProperty
    semantics in isolation.  The end-to-end test (sim task + override over
    HTTP) lands in create_app()'s tests once app/main.py exists.
    """
    points.register_points(Registry.instance())
    app = FastAPI()
    app.include_router(objects_router)
    return TestClient(app)


def test_list_objects(client):
    resp = client.get("/objects")
    assert resp.status_code == 200
    names = {o["name"] for o in resp.json()}
    assert "AHU1-ZN-T" in names and len(names) == 8


def test_read_present_value(client):
    resp = client.get("/objects/analog-input/1/properties/present-value")
    assert resp.status_code == 200
    assert resp.json()["value"] == pytest.approx(22.0)


def test_read_unknown_object_is_404(client):
    assert client.get("/objects/analog-input/99/properties/present-value").status_code == 404


def test_read_unknown_property_is_404(client):
    assert client.get("/objects/analog-input/1/properties/flux-capacitance").status_code == 404


def test_override_and_relinquish_via_http(client):
    url = "/objects/analog-output/1/properties/present-value"
    # control program (stand-in for the PID) at priority 16
    assert client.post(url, json={"value": 30.0, "priority": 16}).status_code == 200
    # operator override at 8 beats it
    assert client.post(url, json={"value": 70.0, "priority": 8}).status_code == 200
    assert client.get(url).json()["value"] == 70.0
    # relinquish = write null at that priority (faithful to BACnet)
    assert client.post(url, json={"value": None, "priority": 8}).status_code == 200
    assert client.get(url).json()["value"] == 30.0


def test_write_setpoint_needs_no_priority(client):
    url = "/objects/analog-value/1/properties/present-value"
    assert client.post(url, json={"value": 24.0}).status_code == 200
    assert client.get(url).json()["value"] == 24.0


def test_write_to_sensor_is_403(client):
    url = "/objects/analog-input/1/properties/present-value"
    assert client.post(url, json={"value": 99.0}).status_code == 403


def test_write_to_non_present_value_property_is_403(client):
    url = "/objects/analog-output/1/properties/object-name"
    assert client.post(url, json={"value": 99.0}).status_code == 403


def test_commandable_write_without_priority_is_422(client):
    url = "/objects/analog-output/1/properties/present-value"
    assert client.post(url, json={"value": 50.0}).status_code == 422


def test_priority_out_of_range_is_422(client):
    url = "/objects/analog-output/1/properties/present-value"
    assert client.post(url, json={"value": 50.0, "priority": 17}).status_code == 422


def _fast_env(monkeypatch, tmp_path):
    """Run the sim fast and keep the trend DB out of the repo."""
    monkeypatch.setenv("AHU_SPEED_FACTOR", "50")
    monkeypatch.setenv("AHU_TREND_INTERVAL", "2")  # sim-seconds between samples
    monkeypatch.setenv("AHU_DB_PATH", str(tmp_path / "history.db"))


def test_trends_accumulate(monkeypatch, tmp_path):
    _fast_env(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        import time

        time.sleep(0.6)
        data = client.get("/trends/analog-input/1", params={"limit": 50}).json()
        assert data["point"] == "AHU1-ZN-T"
        assert len(data["samples"]) >= 2
        assert all(5.0 < s["value"] < 40.0 for s in data["samples"])

        assert client.get("/trends/analog-input/99").status_code == 404


def test_alarm_fires_and_acks_via_api(monkeypatch, tmp_path):
    _fast_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AHU_HIGH_TEMP_LIMIT", "20")  # zone starts at 25 -> fires
    with TestClient(create_app()) as client:
        import time

        time.sleep(0.3)
        alarms = client.get("/alarms").json()
        assert len(alarms) == 1
        assert alarms[0]["state"] == "active-unacked"
        assert "AHU1-ZN-T" in alarms[0]["point"]

        acked = client.post(f"/alarms/{alarms[0]['id']}/ack")
        assert acked.status_code == 200
        assert acked.json()["state"] == "active-acked"

        assert client.post("/alarms/999/ack").status_code == 404


def test_cov_pushes_on_change(monkeypatch, tmp_path):
    _fast_env(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        with client.websocket_connect("/cov") as ws:
            ws.send_json({"subscribe": ["analog-output/1"]})
            first = ws.receive_json()  # initial snapshot for each subscription
            assert first["object"] == "analog-output/1"

            client.post(
                "/objects/analog-output/1/properties/present-value",
                json={"value": 99.0, "priority": 8},
            )
            for _ in range(20):
                msg = ws.receive_json()
                if msg["value"] == 99.0:
                    break
            else:
                pytest.fail("no COV notification for the override")


def test_cors_allows_browser_frontends():
    with TestClient(create_app()) as client:
        # simple cross-origin request (what fetch() sends)
        resp = client.get("/devices", headers={"Origin": "http://localhost:5173"})
        assert resp.headers.get("access-control-allow-origin") == "*"

        # preflight (what the browser sends before a POST with a JSON body)
        resp = client.options(
            "/objects/analog-output/1/properties/present-value",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "*"
        assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_full_app_discovery_and_live_sim():
    """End to end: lifespan starts the sim task; discovery sees the device."""
    with TestClient(create_app()) as client:
        resp = client.get("/devices")
        assert resp.status_code == 200
        (device,) = resp.json()
        assert device["object-name"] == "AHU-1"
        assert device["device-instance"] == 1001
        assert len(device["objects"]) == 8

        # The sim task is genuinely running: zone temp is a live, plausible number
        resp = client.get("/objects/analog-input/1/properties/present-value")
        assert 5.0 < resp.json()["value"] < 40.0
