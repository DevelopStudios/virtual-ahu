# virtual-ahu/tests/test_priority_array.py
import pytest
from app.bacnet.registry import Registry
from app.bacnet.points import AO_COOLING_VALVE

@pytest.fixture
def reg():
    return Registry.instance()

def test_priority_override_and_relinquish(reg):
    # Ensure the valve starts at its default (0 %)
    assert AO_COOLING_VALVE.properties[85] == 0.0

    # 1️⃣ PID (simulated) writes at the lowest priority (16)
    reg.write_priority("analog-output", 5, priority=16, value=30.0)
    assert AO_COOLING_VALVE.properties[85] == 30.0

    # 2️⃣ Manual operator writes at a higher priority (8)
    reg.write_priority("analog-output", 5, priority=8, value=70.0)
    assert AO_COOLING_VALVE.properties[85] == 70.0

    # 3️⃣ Operator relinquishes priority 8 (writes None)
    reg.write_priority("analog-output", 5, priority=8, value=None)
    # After relinquish the present‑value falls back to the PID slot (30 %)
    assert AO_COOLING_VALVE.properties[85] == 30.0