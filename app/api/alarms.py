"""Alarm routes — list the alarm history and acknowledge alarms."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/alarms")
def list_alarms(request: Request):
    return [asdict(a) for a in request.app.state.alarms.alarms]


@router.post("/alarms/{alarm_id}/ack")
def ack_alarm(alarm_id: int, request: Request):
    try:
        return asdict(request.app.state.alarms.ack(alarm_id))
    except KeyError:
        raise HTTPException(404, f"no such alarm: {alarm_id}")