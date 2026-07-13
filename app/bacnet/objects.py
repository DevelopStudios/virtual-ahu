from __future__ import annotations

from typing import Any, Dict, List

# ---- BACnet property identifiers (tiny subset) ----
PROP_PRESENT_VALUE = 85
PROP_OBJECT_NAME = 77
PROP_UNITS = 73
PROP_STATUS_FLAGS = 111
PROP_PRIORITY_ARRAY = 87
PROP_RELINQUISH_DEFAULT = 104
PROP_OUT_OF_SERVICE = 81
# --------------------------------------------------

# Kebab-case property names (as BACnet spells them) -> property IDs.
# The API layer uses this to resolve URL segments; a miss means 404.
PROPERTY_NAMES: dict[str, int] = {
    "present-value": PROP_PRESENT_VALUE,
    "object-name": PROP_OBJECT_NAME,
    "units": PROP_UNITS,
    "status-flags": PROP_STATUS_FLAGS,
    "priority-array": PROP_PRIORITY_ARRAY,
    "relinquish-default": PROP_RELINQUISH_DEFAULT,
    "out-of-service": PROP_OUT_OF_SERVICE,
}

# Object types that carry a priority array in real BACnet.  Inputs are
# sensors — they are never commandable.  (Analog/binary-values *may* be
# commandable; here they are plain writable points.)
COMMANDABLE_TYPES = {"analog-output", "binary-output"}

# Value objects take plain present-value writes (no priority array here);
# inputs are sensors and reject writes entirely.
WRITABLE_TYPES = {"analog-value", "binary-value"}


class BACnetObject:
    """A single BACnet-style object: type + instance + properties.

    Commandable objects (AO/BO) own a 16-slot priority array and a
    relinquish-default; their present-value is *derived* from the array,
    never written directly.  Non-commandable objects take plain
    present-value writes.
    """

    def __init__(
        self,
        obj_type: str,
        instance: int,
        name: str,
        units: str | None = None,
        relinquish_default: float = 0.0,
        present_value: float = 0.0,
    ):
        self.obj_type = obj_type          # e.g. "analog-input"
        self.instance = instance
        self.name = name
        self.units = units
        self.commandable = obj_type in COMMANDABLE_TYPES
        self.properties: Dict[int, Any] = {
            PROP_OBJECT_NAME: name,
            PROP_UNITS: units,
            PROP_STATUS_FLAGS: {
                "in-alarm": False,
                "fault": False,
                "overridden": False,
                "out-of-service": False,
            },
            PROP_OUT_OF_SERVICE: False,
        }
        if self.commandable:
            self.properties[PROP_PRIORITY_ARRAY] = [None] * 16  # slots 1-16
            self.properties[PROP_RELINQUISH_DEFAULT] = relinquish_default
            self.properties[PROP_PRESENT_VALUE] = relinquish_default
        else:
            self.properties[PROP_PRESENT_VALUE] = present_value

    # -----------------------------------------------------------------
    # Present-value access
    # -----------------------------------------------------------------
    def write_present(self, value: float) -> None:
        """Directly set present-value on a *non-commandable* object."""
        if self.commandable:
            raise ValueError(
                f"{self.name}: present-value of a commandable object is "
                "derived from the priority array; use write_priority()"
            )
        self.properties[PROP_PRESENT_VALUE] = value

    # -----------------------------------------------------------------
    # Priority-array helpers - the heart of a commandable point
    # -----------------------------------------------------------------
    def write_priority(self, priority: int, value: float | None) -> None:
        """
        Write *value* into the given *priority* (1-16). ``None`` relinquishes.
        After the write, present-value is recomputed per BACnet rules.
        """
        if not self.commandable:
            raise ValueError(f"{self.name} ({self.obj_type}) is not commandable")
        if not 1 <= priority <= 16:
            raise ValueError("priority must be in 1..16")
        self.properties[PROP_PRIORITY_ARRAY][priority - 1] = value
        self._recalc_present_value()

    def _recalc_present_value(self) -> None:
        """Highest occupied slot wins; empty array falls back to relinquish-default."""
        pa: List[float | None] = self.properties[PROP_PRIORITY_ARRAY]
        for val in pa:
            if val is not None:
                self.properties[PROP_PRESENT_VALUE] = val
                return
        self.properties[PROP_PRESENT_VALUE] = self.properties[PROP_RELINQUISH_DEFAULT]
