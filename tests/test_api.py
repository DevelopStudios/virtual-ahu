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
