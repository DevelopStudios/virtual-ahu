"""Point registry — the single source of truth for the sim, PID, and API."""

from typing import Dict, Iterable, Tuple

from .objects import BACnetObject, PROP_PRESENT_VALUE


class Registry:
    _instance: "Registry | None" = None

    def __init__(self):
        self._objects: Dict[Tuple[str, int], BACnetObject] = {}

    @classmethod
    def instance(cls) -> "Registry":
        """Process-wide registry used by the running app (tests build their own)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------
    # Registration / lookup
    # -----------------------------------------------------------------
    def register(self, obj: BACnetObject) -> None:
        self._objects[(obj.obj_type, obj.instance)] = obj

    def get(self, obj_type: str, instance: int) -> BACnetObject:
        return self._objects[(obj_type, instance)]

    def all_objects(self) -> Iterable[BACnetObject]:
        return self._objects.values()

    # -----------------------------------------------------------------
    # Read/write helpers used by the simulation, tests, and later the API
    # -----------------------------------------------------------------
    def read_present(self, obj_type: str, instance: int) -> float:
        return self.get(obj_type, instance).properties[PROP_PRESENT_VALUE]

    def write_present(self, obj_type: str, instance: int, value: float) -> None:
        """Plain present-value write (sensors, writable values). Raises on commandable objects."""
        self.get(obj_type, instance).write_present(value)

    def write_priority(
        self, obj_type: str, instance: int, priority: int, value: float | None
    ) -> None:
        self.get(obj_type, instance).write_priority(priority, value)
