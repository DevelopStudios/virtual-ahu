"""Simple thermal model for a single zone.

Three effects move the zone temperature:
* supply air pulls it toward the discharge temperature (fast, tau ~5 min),
* the envelope leaks toward outdoor temperature (slow, tau ~1 h),
* internal gains (people, equipment) add heat at a constant rate when present.

All temperatures are in degrees Celsius.
"""


class Zone:
    """Represent the thermal state of a zone."""

    SUPPLY_TAU = 300.0     # s — coupling to supply air
    ENVELOPE_TAU = 3600.0  # s — coupling to outdoors

    def __init__(self, init_temp: float = 22.0):
        """Create a zone starting at `init_temp` (default 22 °C)."""
        self.temp: float = init_temp

    def step(
        self,
        supply_temp: float,
        dt: float,
        outdoor_temp: float | None = None,
        internal_gain: float = 0.0,
    ) -> None:
        """
        Update the zone temperature.

        * ``supply_temp`` — temperature of the air supplied to the zone.
        * ``dt`` — elapsed simulation time in seconds.
        * ``outdoor_temp`` — envelope losses/gains toward this, if given.
        * ``internal_gain`` — heat load in °C/s (people, equipment).
        """
        self.temp += (supply_temp - self.temp) * dt / self.SUPPLY_TAU
        if outdoor_temp is not None:
            self.temp += (outdoor_temp - self.temp) * dt / self.ENVELOPE_TAU
        self.temp += internal_gain * dt
