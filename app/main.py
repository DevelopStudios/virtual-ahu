"""FastAPI app factory and startup wiring for the virtual AHU.

Three background tasks run on the server's event loop, started by the
lifespan at boot and cancelled at shutdown: the simulation tick loop,
the trend sampler, and the alarm evaluator.  Routers and tasks never
talk to each other — they share only the point registry (and app.state
for the trend/alarm services).
"""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import alarms, cov, devices, objects, trends
from app.bacnet.registry import Registry
from app.config import Settings
from app.history.alarms import AlarmEngine
from app.history.trends import TrendLog
from app.sim.engine import Simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = Settings()
    registry = Registry.instance()
    sim = Simulation(cfg=cfg, registry=registry)

    # Keep references on app.state: an unreferenced Task can be GC'd mid-flight
    app.state.sim = sim
    app.state.trends = TrendLog(cfg.db_path, registry)
    app.state.alarms = AlarmEngine(registry, high_limit=cfg.high_temp_limit)
    app.state.tasks = [
        asyncio.create_task(sim.run_async()),
        asyncio.create_task(app.state.trends.run(cfg.trend_interval / cfg.speed_factor)),
        asyncio.create_task(app.state.alarms.run(cfg.tick_rate / cfg.speed_factor)),
    ]
    yield
    for task in app.state.tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    app.state.trends.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Virtual AHU", lifespan=lifespan)
    app.include_router(devices.router)
    app.include_router(objects.router)
    app.include_router(trends.router)
    app.include_router(alarms.router)
    app.include_router(cov.router)
    return app
