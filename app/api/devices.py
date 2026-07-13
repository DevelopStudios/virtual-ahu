"""Device discovery — the REST stand-in for BACnet Who-Is/I-Am."""

from fastapi import APIRouter

from app.bacnet.registry import Registry

router = APIRouter()

DEVICE_INSTANCE = 1001
DEVICE_NAME = "AHU-1"


@router.get("/devices")
def list_devices():
    """One device today; Phase 7's chiller joins this list without a shape change."""
    return [
        {
            "device-instance": DEVICE_INSTANCE,
            "object-name": DEVICE_NAME,
            "objects": [
                {"type": o.obj_type, "instance": o.instance, "name": o.name}
                for o in Registry.instance().all_objects()
            ],
        }
    ]
