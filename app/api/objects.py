"""ReadProperty / WriteProperty routes — a thin HTTP shell over the registry.

All semantics (commandability, priority rules, derived present-value) live
in the BACnet layer; this module only translates HTTP to registry calls and
BACnet outcomes to status codes:

* unknown object or property        -> 404
* write to a read-only point/prop   -> 403 (BACnet write-access-denied)
* bad or missing priority           -> 422
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.bacnet.objects import (
    PROPERTY_NAMES,
    WRITABLE_TYPES,
    BACnetObject,
)
from app.bacnet.registry import Registry

router = APIRouter()


class WriteRequest(BaseModel):
    value: float | int | bool | None = None
    priority: int | None = None


def _get_object(obj_type: str, instance: int) -> BACnetObject:
    try:
        return Registry.instance().get(obj_type, instance)
    except KeyError:
        raise HTTPException(404, f"no such object: {obj_type},{instance}")


def _property_id(prop: str) -> int:
    try:
        return PROPERTY_NAMES[prop]
    except KeyError:
        raise HTTPException(404, f"no such property: {prop}")


@router.get("/objects")
def list_objects():
    return [
        {"type": o.obj_type, "instance": o.instance, "name": o.name}
        for o in Registry.instance().all_objects()
    ]


@router.get("/objects/{obj_type}/{instance}/properties/{prop}")
def read_property(obj_type: str, instance: int, prop: str):
    obj = _get_object(obj_type, instance)
    prop_id = _property_id(prop)
    if prop_id not in obj.properties:
        raise HTTPException(404, f"{obj.name} has no property {prop}")
    return {"value": obj.properties[prop_id]}


@router.post("/objects/{obj_type}/{instance}/properties/{prop}")
def write_property(obj_type: str, instance: int, prop: str, body: WriteRequest):
    obj = _get_object(obj_type, instance)
    _property_id(prop)
    if prop != "present-value":
        raise HTTPException(403, f"property {prop} is not writable")

    if obj.commandable:
        if body.priority is None:
            raise HTTPException(422, f"{obj.name} is commandable; priority required")
        try:
            obj.write_priority(body.priority, body.value)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
    elif obj.obj_type in WRITABLE_TYPES:
        obj.write_present(body.value)
    else:
        raise HTTPException(403, f"{obj.name} ({obj.obj_type}) is read-only")

    return {"value": obj.properties[PROPERTY_NAMES["present-value"]]}
