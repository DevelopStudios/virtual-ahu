"""AHU-1 point definitions.

Call :func:`register_points` to populate a :class:`Registry`.  The
``(object-type, instance)`` address constants below are how the engine,
tests, and later the API refer to individual points.  Instance numbers
are per object type, as in real BACnet.
"""

from .objects import BACnetObject
from .registry import Registry

# (object-type, instance) addresses
ZONE_TEMP = ("analog-input", 1)      # AHU1-ZN-T   zone temperature
SUPPLY_TEMP = ("analog-input", 2)    # AHU1-SA-T   supply (discharge) air temp
OUTDOOR_TEMP = ("analog-input", 3)   # AHU1-OA-T   outdoor air temp
ZONE_SETPOINT = ("analog-value", 1)  # AHU1-ZN-SP  zone setpoint (writable)
COOLING_VALVE = ("analog-output", 1) # AHU1-CLG-V  cooling valve (commandable)
FAN_CMD = ("binary-output", 1)       # AHU1-SF-C   supply fan command (commandable)
FAN_STATUS = ("binary-input", 1)     # AHU1-SF-S   supply fan status
OCCUPANCY = ("binary-value", 1)      # AHU1-OCC    occupancy mode (writable)


def register_points(reg: Registry) -> None:
    """Create every AHU-1 point and register it, with sane initial values."""

    def make(address, name, units=None, **kwargs):
        obj_type, instance = address
        reg.register(BACnetObject(obj_type, instance, name, units=units, **kwargs))

    # Sensors (AI/BI) — plain present-value, written by the simulation
    make(ZONE_TEMP, "AHU1-ZN-T", units="°C", present_value=22.0)
    make(SUPPLY_TEMP, "AHU1-SA-T", units="°C", present_value=22.0)
    make(OUTDOOR_TEMP, "AHU1-OA-T", units="°C", present_value=15.0)
    make(FAN_STATUS, "AHU1-SF-S", present_value=0)

    # Writable values (AV/BV) — plain present-value, written by operators
    make(ZONE_SETPOINT, "AHU1-ZN-SP", units="°C", present_value=22.0)
    make(OCCUPANCY, "AHU1-OCC", present_value=1)

    # Commandable outputs (AO/BO) — priority array; present-value is derived.
    # Fan relinquish-default is 1 ("auto = run") so the AHU runs out of the box.
    make(COOLING_VALVE, "AHU1-CLG-V", units="%", relinquish_default=0.0)
    make(FAN_CMD, "AHU1-SF-C", relinquish_default=1)
