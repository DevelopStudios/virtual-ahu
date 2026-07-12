"""Orchestrates the simulation loop for the virtual AHU.

Every value flows through the point registry: the sim writes sensor
readings in, the PID reads its process variable and setpoint out, and
the zone physics responds to the cooling valve's *present-value* — so a
manual override at priority 8 genuinely changes the room, not just a
number.  Phase 4 runs this same loop as an asyncio task under FastAPI.
"""

import time

from app.bacnet import points
from app.bacnet.registry import Registry
from app.config import Settings
from app.sim.pid import PID
from app.sim.weather import outdoor_temp
from app.sim.zone import Zone

# Conventional priority slots: 8 = manual operator, 16 = control program
PID_PRIORITY = 16

COIL_DISCHARGE_TEMP = 13.0  # °C supply air at 100 % cooling
OCCUPIED_GAIN = 0.005       # °C/s heat load from people/equipment when occupied


class Simulation:
    def __init__(self, cfg: Settings | None = None, registry: Registry | None = None):
        self.cfg = cfg or Settings()
        self.registry = registry if registry is not None else Registry.instance()
        points.register_points(self.registry)
        self.zone = Zone(init_temp=25.0)  # start warm so the cooling loop has work to do
        # Cooling is direct-acting (hotter zone -> more output); this PID is
        # reverse-acting, so we clamp to (-100, 0) and negate in tick().
        self.pid = PID(kp=15.0, ki=0.05, output_limits=(-100.0, 0.0))
        self.t = 0.0

    def tick(self) -> None:
        """Advance the simulation by one tick. No sleeping, no printing."""
        reg = self.registry
        dt = self.cfg.tick_rate

        # 1. Sensor readings into the registry
        reg.write_present(*points.ZONE_TEMP, self.zone.temp)
        reg.write_present(*points.OUTDOOR_TEMP, outdoor_temp(self.t))

        # 2. PID reads its process variable and setpoint from the registry
        self.pid.setpoint = reg.read_present(*points.ZONE_SETPOINT)
        zone_temp = reg.read_present(*points.ZONE_TEMP)
        valve_cmd = -self.pid.update(measured=zone_temp, dt=dt)

        # 3. PID output -> cooling valve at the control-program priority
        reg.write_priority(*points.COOLING_VALVE, PID_PRIORITY, valve_cmd)

        # 4. Physics responds to present-values (which an override may control)
        valve = reg.read_present(*points.COOLING_VALVE)
        fan_on = bool(reg.read_present(*points.FAN_CMD))
        reg.write_present(*points.FAN_STATUS, int(fan_on))  # ideal fan: status tracks command

        supply = self.zone.temp + (COIL_DISCHARGE_TEMP - self.zone.temp) * valve / 100.0
        reg.write_present(*points.SUPPLY_TEMP, supply)

        oa = reg.read_present(*points.OUTDOOR_TEMP)
        occupied = bool(reg.read_present(*points.OCCUPANCY))
        gain = OCCUPIED_GAIN if occupied else 0.0
        if fan_on:
            self.zone.step(supply_temp=supply, dt=dt, outdoor_temp=oa, internal_gain=gain)
        else:
            # No airflow: only envelope losses and internal gains act
            self.zone.step(supply_temp=self.zone.temp, dt=dt, outdoor_temp=oa, internal_gain=gain)

        self.t += dt

    def run(self) -> None:
        """Tick forever at the configured rate, printing from the registry."""
        reg = self.registry
        while True:
            self.tick()
            print(
                f"[t={self.t:7.1f}s]"
                f" zone={reg.read_present(*points.ZONE_TEMP):5.2f}°C"
                f" sp={reg.read_present(*points.ZONE_SETPOINT):5.2f}°C"
                f" outdoor={reg.read_present(*points.OUTDOOR_TEMP):5.2f}°C"
                f" supply={reg.read_present(*points.SUPPLY_TEMP):5.2f}°C"
                f" valve={reg.read_present(*points.COOLING_VALVE):5.1f}%"
                f" fan={'ON' if reg.read_present(*points.FAN_STATUS) else 'OFF'}"
            )
            time.sleep(self.cfg.tick_rate / self.cfg.speed_factor)


if __name__ == "__main__":
    Simulation().run()
