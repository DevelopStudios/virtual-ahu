"""Orchestrates the simulation loop for the virtual AHU.

The loop creates a ``Zone`` instance, reads the outdoor temperature,
steps the zone, and prints a concise status line each tick.
Later phases will replace the placeholder supply temperature with a PID
output and will hook the loop into FastAPI.
"""

import time
from zone import Zone
from weather import outdoor_temp
from config import Settings
from app.sim.pid import PID


def run() -> None:
    """Start the simulation loop."""
    cfg = Settings()                     # Grab env-configured settings
    zone = Zone()                        # Initial zone temperature ~22 °C
    zone.temp = 18.0                     # Start colder to create a PID error
    pid = PID(kp=2.0, ki=0.5, setpoint=22.0, output_limits=(-100.0, 100.0))
    start = time.time()                 # Reference time = 0
    max_ticks = 10
    tick = 0
    while tick < max_ticks:
        t = time.time() - start
        oa = outdoor_temp(t)
        command = pid.update(measured=zone.temp, dt=cfg.tick_rate)
        min_sa, max_sa = 10.0, 30.0
        # Supply temperature is the setpoint plus the PID correction,
        # clamped to a realistic range.
        supply_temp = max(min_sa, min(max_sa, pid.setpoint + command))
        zone.step(supply_temp=supply_temp, dt=cfg.tick_rate)
        print(
            f"[t={t:6.1f}s] zone={zone.temp:5.2f}°C outdoor={oa:5.2f}°C supply={supply_temp:5.2f}°C pid_cmd={command:5.2f}"
        )
        time.sleep(cfg.tick_rate / cfg.speed_factor)
        tick += 1


if __name__ == "__main__":
    run()
