import pytest
from app.sim.pid import PID

@pytest.fixture
def pid():
    # A tiny PI controller (kp=0, ki=1) for deterministic testing.
    return PID(kp=0.0, ki=1.0, setpoint=20.0, output_limits=(-100.0, 100.0))

def test_loop_settles_at_setpoint_with_load():
    """
    With an occupied zone (internal heat gain), the closed loop must settle
    AT the setpoint with the valve doing steady work — not sag below it
    with the valve shut, which is what happens when the zone has no load.
    """
    from app.bacnet import points
    from app.bacnet.registry import Registry
    from app.sim.engine import Simulation

    sim = Simulation(registry=Registry())
    for _ in range(7200):  # two simulated hours
        sim.tick()

    zone = sim.registry.read_present(*points.ZONE_TEMP)
    sp = sim.registry.read_present(*points.ZONE_SETPOINT)
    valve = sim.registry.read_present(*points.COOLING_VALVE)
    assert zone == pytest.approx(sp, abs=0.3)
    assert valve > 2.0  # steady cooling holds off the heat load


def test_integral_accumulates(pid):
    """
    With a constant error of +10 °C (setpoint 20 measured 10),
    each second the integral term should grow by 10.
    """
    out1 = pid.update(measured=10.0, dt=1.0)   # error = 10
    out2 = pid.update(measured=10.0, dt=1.0)   # another second, same error

    assert out1 == pytest.approx(10.0)   # 1 * 10 * 1
    assert out2 == pytest.approx(20.0)   # cumulative integral = 20