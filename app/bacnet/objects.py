from __future__ import annotations
from typing import Any, Dict, List

# ---- BACnet property identifiers (tiny subset) ----
PROP_PRESENT_VALUE = 85
PROP_OBJECT_NAME = 77
PROP_UNITS = 73
PROP_STATUS_FLAGS = 111
PROP_PRIORITY_ARRAY = 87
PROP_RELINQUISH_DEFAULT = 92
# --------------------------------------------------

class BACnetObject:
    """Base class for all BACnet objects.

    ``properties`` holds a mapping from property ID to the current value.
    Sub‑classes can add more convenience methods, but the core registry only
    needs the fields below.
    """

    def __init__(self, obj_type: str, instance: int, name: str, units: str | None = None):
        self.obj_type = obj_type          # e.g. "analog-input"
        self.instance = instance
        self.name = name
        self.units = units
        self.properties: Dict[int, Any] = {
            PROP_OBJECT_NAME: name,
            PROP_PRESENT_VALUE: 0.0,
            PROP_UNITS: units,
            PROP_STATUS_FLAGS: [],
            PROP_PRIORITY_ARRAY: [None] * 16,   # slots 1‑16 (index 0‑15)
            PROP_RELINQUISH_DEFAULT: 0.0,
        }

    # -----------------------------------------------------------------
    # Priority‑array helpers – the heart of a commandable point
    # -----------------------------------------------------------------
    def write_priority(self, priority: int, value: float | None) -> None:
        """
        Write *value* into the given *priority* (1 16). ``None`` relinquishes.
        After the write we recompute ``present value`` according to BACnet rules.
        """
        if not 1 <= priority <= 16:
            raise ValueError("priority must be in 1..16")
        self.properties[PROP_PRIORITY_ARRAY][priority - 1] = value
        self._recalc_present_value()

    def _recalc_present_value(self) -> None:
        """Apply BACnet priority-array semantics to set ``present value``."""
        pa: List[float | None] = self.properties[PROP_PRIORITY_ARRAY]
        for val in pa:
            if val is not None:
                self.properties[PROP_PRESENT_VALUE] = val
                return
        # All slots cleared → fall back to relinquish‑default
        self.properties[PROP_PRESENT_VALUE] = self.properties[PROP_RELINQUISH_DEFAULT]