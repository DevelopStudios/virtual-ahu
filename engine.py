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

def run() -> None:
    """Start the simulation loop."""
    cfg = Settings() #Grab env-configured settings
    zone = Zone()   #Initial zone temprature 22C
    start = time.time()  #Reference time = 0

    max_ticks = 10
    tick = 0
    while tick < max_ticks:
        t = time.time() - start #Simulation elapsed seconds
        oa = outdoor_temp(t) #Outdoor temperature for this tick

        supply_temp = oa

        #Advance the zone model
        zone.step(supply_temp=supply_temp, dt=cfg.tick_rate)

        #Print a one-line status report
        print(
            f"[t={t:6.1f}s] zone={zone.temp:5.2f}°C "
            f"outdoor={oa:5.2f}°C supply={supply_temp:5.2f}°C"
        )

        #Respect the configured tick rate and optional speed-up factor
        time.sleep(cfg.tick_rate / cfg.speed_factor)
        tick += 1

if __name__ == "__main__":
    run()