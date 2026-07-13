"""SQLite trend logging — the Niagara "History extension" equivalent.

A sampler task periodically snapshots every registered point's
present-value into a samples table.  On a PaaS the file is ephemeral:
this is history since last boot, not an archive.
"""

import asyncio
import sqlite3
import time

from app.bacnet.objects import PROP_PRESENT_VALUE
from app.bacnet.registry import Registry


class TrendLog:
    def __init__(self, db_path, registry: Registry):
        self.registry = registry
        # check_same_thread=False: FastAPI runs sync routes in a threadpool,
        # so reads come from worker threads while the sampler writes from
        # the event-loop thread.  SQLite serializes access internally.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS samples ("
            " ts REAL NOT NULL,"
            " obj_type TEXT NOT NULL,"
            " instance INTEGER NOT NULL,"
            " value REAL NOT NULL)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_samples"
            " ON samples (obj_type, instance, ts)"
        )
        self.conn.commit()

    def record_sample(self) -> None:
        """Snapshot every point's present-value into the samples table."""
        ts = time.time()
        rows = [
            (ts, o.obj_type, o.instance, float(o.properties[PROP_PRESENT_VALUE]))
            for o in self.registry.all_objects()
        ]
        with self.conn:
            self.conn.executemany("INSERT INTO samples VALUES (?, ?, ?, ?)", rows)

    def query(self, obj_type: str, instance: int, limit: int = 100) -> list[dict]:
        """Newest-first samples for one point."""
        cur = self.conn.execute(
            "SELECT ts, value FROM samples"
            " WHERE obj_type = ? AND instance = ?"
            " ORDER BY ts DESC LIMIT ?",
            (obj_type, instance, limit),
        )
        return [{"ts": ts, "value": value} for ts, value in cur]

    def close(self) -> None:
        self.conn.close()

    async def run(self, interval: float) -> None:
        """Sample forever every *interval* real seconds."""
        while True:
            self.record_sample()
            await asyncio.sleep(interval)