"""Generate an outdoor-temperature sine wave that mimics a 24h day."""

import math

def outdoor_temp(t: float, amplitude: float = 10.0, base: float = 15.0) -> float:
    """
    Return the outdoor temperature at simulation time ``t``.

    * ``t`` - elapsed seconds since the simulation start.
    * ``amplitude`` - swing around the base temperature (default 10 °C).
    * ``base`` - average outdoor temperature (default 15 °C).

    The function uses a 24 h period (86 400 s).
    """

    # Angular frequency for a 24-hour cycle
    omega = 2 * math.pi / 86_400
    return base + amplitude * math.sin(omega * t)