import pytest
from app.sim.pid import PID

@pytest.fixture
def pid():
    # A tiny PI controller (kp=0, ki=1) for deterministic testing.
    return PID(kp=0.0, ki=1.0, setpoint=20.0, output_limits=(-100.0, 100.0))

def test_integral_accumulates(pid):
    """
    With a constant error of +10 °C (setpoint 20 measured 10),
    each second the integral term should grow by 10.
    """
    out1 = pid.update(measured=10.0, dt=1.0)   # error = 10
    out2 = pid.update(measured=10.0, dt=1.0)   # another second, same error

    assert out1 == pytest.approx(10.0)   # 1 * 10 * 1
    assert out2 == pytest.approx(20.0)   # cumulative integral = 20