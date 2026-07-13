"""High-zone-temp alarm: evaluation, deadband, and ack state.

State machine per alarm: active-unacked -> active-acked -> cleared
(clearing also works from unacked; real BACnet tracks ack per transition,
this is the useful subset).  The deadband prevents chattering: fire above
the limit, clear only below limit - deadband.  While active, the zone-temp
point's in-alarm status flag is raised.
"""

import asyncio
import itertools
import time
from dataclasses import dataclass

from app.bacnet import points
from app.bacnet.objects import PROP_STATUS_FLAGS
from app.bacnet.registry import Registry


@dataclass
class Alarm:
    id: int
    point: str
    message: str
    raised_at: float
    state: str = "active-unacked"  # active-unacked | active-acked | cleared
    cleared_at: float | None = None


class AlarmEngine:
    def __init__(self, registry: Registry, high_limit: float = 26.0, deadband: float = 1.0):
        self.registry = registry
        self.high_limit = high_limit
        self.deadband = deadband
        self.alarms: list[Alarm] = []
        self._ids = itertools.count(1)
        self._active: Alarm | None = None

    def evaluate(self) -> None:
        zone = self.registry.get(*points.ZONE_TEMP)
        temp = self.registry.read_present(*points.ZONE_TEMP)

        if self._active is None and temp > self.high_limit:
            self._active = Alarm(
                id=next(self._ids),
                point=zone.name,
                message=f"high zone temp: {temp:.1f} °C > {self.high_limit:.1f} °C limit",
                raised_at=time.time(),
            )
            self.alarms.append(self._active)
            zone.properties[PROP_STATUS_FLAGS]["in-alarm"] = True
        elif self._active is not None and temp < self.high_limit - self.deadband:
            self._active.state = "cleared"
            self._active.cleared_at = time.time()
            self._active = None
            zone.properties[PROP_STATUS_FLAGS]["in-alarm"] = False

    def ack(self, alarm_id: int) -> Alarm:
        """Acknowledge an alarm. Raises KeyError for an unknown id."""
        for alarm in self.alarms:
            if alarm.id == alarm_id:
                if alarm.state == "active-unacked":
                    alarm.state = "active-acked"
                return alarm
        raise KeyError(alarm_id)

    async def run(self, interval: float) -> None:
        """Evaluate forever every *interval* real seconds."""
        while True:
            self.evaluate()
            await asyncio.sleep(interval)