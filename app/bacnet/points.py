"""Instantiate every point defined in the specification and register them."""

from .objects import BACnetObject
from .registry import Registry

reg = Registry.instance()

# Helper to avoid repetition -------------------------------------------------
def _make(obj_type: str, instance: int, name: str, units: str | None = None) -> BACnetObject:
    obj = BACnetObject(obj_type=obj_type, instance=instance, name=name, units=units)
    reg.register(obj)
    return obj
# --------------------------------------------------------------------------

# Analog‑Input (AI) – read‑only sensor values
AI_ZONE_TEMP      = _make("analog-input", 1, "AHU1‑ZN‑T", units="°C")
AI_SUPPLY_TEMP    = _make("analog-input", 2, "AHU1‑SA‑T", units="°C")
AI_OUTDOOR_TEMP   = _make("analog-input", 3, "AHU1‑OA‑T", units="°C")

# Analog‑Value (AV) – writable setpoint
AV_ZONE_SP        = _make("analog-value", 4, "AHU1‑ZN‑SP", units="°C")

# Analog‑Output (AO) – commandable points (priority‑array)
AO_COOLING_VALVE = _make("analog-output", 5, "AHU1‑CLG‑V", units="%")
AO_FAN_CMD        = _make("analog-output", 6, "AHU1‑SF‑C", units="%")

# Binary‑Input (BI) – read‑only status bits
BI_FAN_STATUS    = _make("binary-input", 7, "AHU1‑SF‑S")

# Binary‑Value (BV) – writable binary point
BV_OCCUPANCY      = _make("binary-value", 8, "AHU1‑OCC")

# High‑zone‑temp alarm (treated as an analog‑input for simplicity)
AI_HIGH_TEMP_ALARM = _make("analog-input", 9, "AHU1‑HIGH‑TEMP‑ALARM")

# --------------------------------------------------------------------------
# Set initial present‑values that make sense for a freshly‑started simulation.
# You can change these defaults later if you wish.
AI_ZONE_TEMP.properties[85]      = 22.0
AI_SUPPLY_TEMP.properties[85]    = 22.0
AI_OUTDOOR_TEMP.properties[85]   = 15.0
AV_ZONE_SP.properties[85]         = 22.0
AO_COOLING_VALVE.properties[85]  = 0.0
AO_FAN_CMD.properties[85]        = 0.0
BI_FAN_STATUS.properties[85]     = 0
BV_OCCUPANCY.properties[85]    = 0
AI_HIGH_TEMP_ALARM.properties[85] = 0