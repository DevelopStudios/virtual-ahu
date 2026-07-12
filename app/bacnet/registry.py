"""Global point registry used by the simulation, PID, and later the FastAPI layer."""

from typing import Dict, Tuple
from .objects import BACnetObject, PROP_PRESENT_VALUE, PROP_PRIORITY_ARRAY

class Registry:
    _instance: "Registry | None" = None

    def __init__(self):
        self._objects: Dict[Tuple[str, int], BACnetObject] = {}

    @classmethod
    def instance(cls) -> "Registry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------
    # Registration API
    # -----------------------------------------------------------------
    def register(self, obj: BACnetObject) -> None:
        key = (obj.obj_type, obj.instance)
        self._objects[key] = obj

    def get(self, obj_type: str, instance: int) -> BACnetObject:
        return self._objects[(obj_type, instance)]

    # -----------------------------------------------------------------
    # Simple read/write helpers used by the simulation and tests
    # -----------------------------------------------------------------
    def read_present(self, obj_type: str, instance: int) -> float:
        obj = self.get(obj_type, instance)
        return obj.properties[PROP_PRESENT_VALUE]

    def write_priority(self, obj_type: str, instance: int, priority: int, value: float | None) -> None:
        obj = self.get(obj_type, instance)
        obj.write_priority(priority, value)