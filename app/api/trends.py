"""Trend query routes — read the SQLite history the sampler task writes."""

from fastapi import APIRouter, HTTPException, Request

from app.bacnet.registry import Registry

router = APIRouter()


@router.get("/trends/{obj_type}/{instance}")
def get_trend(obj_type: str, instance: int, request: Request, limit: int = 100):
    try:
        obj = Registry.instance().get(obj_type, instance)
    except KeyError:
        raise HTTPException(404, f"no such object: {obj_type},{instance}")
    samples = request.app.state.trends.query(obj_type, instance, limit)
    return {"point": obj.name, "samples": samples}