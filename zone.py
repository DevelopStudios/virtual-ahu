"""Simple thermal model for a single zone.

The model is deliberately tiny - you will later plug a PID controller
into it.  All temperatures are in degrees Celsius.
"""

class Zone:
    """Represent the thermal state of a zone."""

    def __init__(self, init_temp: float = 22.0):
        """Create a zone starting at `init_temp` (default 22 °C)."""
        self.temp: float = init_temp
    
    def step(self, supply_temp: float, dt: float) -> None:
        """
        Update the zone temperature.

        * ``supply_temp`` - temperature of the air supplied to the zone.
        * ``dt`` - elapsed simulation time in seconds.
        """
        tau = 300.0
        self.temp += (supply_temp - self.temp) * dt / tau
        pass

    
    