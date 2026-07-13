"""Change-of-Value subscriptions over WebSocket.

A client connects, sends {"subscribe": ["analog-input/1", ...]}, and gets
an initial snapshot of each point followed by a push whenever a value
moves by at least COV_INCREMENT.  This mimics BACnet SubscribeCOV: the
supervisor doesn't poll — the device notifies on change.
"""

import time

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.bacnet.registry import Registry

router = APIRouter()

COV_INCREMENT = 0.1


def _parse_subscriptions(message: dict) -> list[tuple[str, int]]:
    addresses = []
    for item in message.get("subscribe", []):
        obj_type, _, instance = item.partition("/")
        addresses.append((obj_type, int(instance)))
    return addresses


@router.websocket("/cov")
async def cov_feed(ws: WebSocket):
    await ws.accept()
    addresses = _parse_subscriptions(await ws.receive_json())
    registry = Registry.instance()
    cfg = ws.app.state.sim.cfg
    poll_interval = cfg.tick_rate / cfg.speed_factor

    last_sent: dict[tuple[str, int], float] = {}
    try:
        while True:
            for address in addresses:
                try:
                    obj = registry.get(*address)
                except KeyError:
                    continue
                value = registry.read_present(*address)
                previous = last_sent.get(address)
                if previous is None or abs(value - previous) >= COV_INCREMENT:
                    last_sent[address] = value
                    await ws.send_json(
                        {
                            "object": f"{address[0]}/{address[1]}",
                            "name": obj.name,
                            "value": value,
                            "ts": time.time(),
                        }
                    )
            await asyncio.sleep(poll_interval)
    except (WebSocketDisconnect, RuntimeError):
        return