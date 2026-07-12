# virtual-ahu/tests/test_priority_array.py
import pytest

from app.bacnet.objects import (
    PROP_OUT_OF_SERVICE,
    PROP_PRESENT_VALUE,
    PROP_STATUS_FLAGS,
)
from app.bacnet.registry import Registry
from app.bacnet import points
from app.config import Settings
from app.sim.engine import Simulation


@pytest.fixture
def reg():
    """A fresh, fully populated registry per test — no shared singleton state."""
    r = Registry()
    points.register_points(r)
    return r


def test_priority_override_and_relinquish(reg):
    # Valve starts at its relinquish-default (0 %)
    assert reg.read_present(*points.COOLING_VALVE) == 0.0

    # PID writes at the control-program priority (16)
    reg.write_priority(*points.COOLING_VALVE, priority=16, value=30.0)
    assert reg.read_present(*points.COOLING_VALVE) == 30.0

    # Manual operator overrides at priority 8 — beats the loop
    reg.write_priority(*points.COOLING_VALVE, priority=8, value=70.0)
    assert reg.read_present(*points.COOLING_VALVE) == 70.0

    # Operator relinquishes (writes None) — falls back to the PID slot
    reg.write_priority(*points.COOLING_VALVE, priority=8, value=None)
    assert reg.read_present(*points.COOLING_VALVE) == 30.0

    # Relinquish the PID slot too — falls back to relinquish-default
    reg.write_priority(*points.COOLING_VALVE, priority=16, value=None)
    assert reg.read_present(*points.COOLING_VALVE) == 0.0


def test_point_names_are_plain_ascii(reg):
    for obj in reg.all_objects():
        assert obj.name.isascii(), f"{obj.name!r} contains non-ASCII characters"


def test_fan_command_is_a_binary_output(reg):
    obj_type, instance = points.FAN_CMD
    assert obj_type == "binary-output"
    assert reg.get(obj_type, instance).name == "AHU1-SF-C"


def test_sensors_are_not_commandable(reg):
    # An analog-input has no priority array; writing one must be rejected
    with pytest.raises(ValueError):
        reg.write_priority(*points.ZONE_TEMP, priority=8, value=99.0)


def test_commandable_present_value_cannot_be_written_directly(reg):
    # Present-value of a commandable object is derived from the priority
    # array; a direct write would silently bypass any active override.
    with pytest.raises(ValueError):
        reg.write_present(*points.COOLING_VALVE, 55.0)


def test_status_flags_and_out_of_service_exist(reg):
    obj = reg.get(*points.ZONE_TEMP)
    flags = obj.properties[PROP_STATUS_FLAGS]
    assert set(flags) == {"in-alarm", "fault", "overridden", "out-of-service"}
    assert obj.properties[PROP_OUT_OF_SERVICE] is False


def test_engine_override_beats_pid_and_relinquish_restores(reg):
    sim = Simulation(cfg=Settings(), registry=reg)

    # Let the loop run: zone starts above setpoint, so the PID should
    # command some cooling at priority 16.
    for _ in range(5):
        sim.tick()
    pid_valve = reg.read_present(*points.COOLING_VALVE)
    assert 0.0 < pid_valve <= 100.0

    # Operator forces the valve fully open at priority 8
    reg.write_priority(*points.COOLING_VALVE, priority=8, value=100.0)
    sim.tick()
    # The PID wrote at 16 during that tick, but the override must win...
    assert reg.read_present(*points.COOLING_VALVE) == 100.0
    # ...and the physics must respond to the override, not the PID value:
    # full cooling drives supply air toward the coil discharge temperature.
    zone_temp = reg.read_present(*points.ZONE_TEMP)
    assert reg.read_present(*points.SUPPLY_TEMP) < zone_temp

    # Release the override — the very next tick, the PID is back in control
    reg.write_priority(*points.COOLING_VALVE, priority=8, value=None)
    sim.tick()
    valve_after = reg.read_present(*points.COOLING_VALVE)
    assert valve_after < 100.0
    assert valve_after > 0.0
