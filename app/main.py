"""FastAPI app factory and startup wiring for the virtual AHU.

The simulation runs as an asyncio task on the server's event loop, started
by the lifespan at boot and cancelled at shutdown.  The API routers and the
sim never talk to each other — they share only the point registry.
"""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import devices, objects
from app.bacnet.registry import Registry
from app.config import Settings
from app.sim.engine import Simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    sim = Simulation(cfg=Settings(), registry=Registry.instance())
    # Keep references on app.state: an unreferenced Task can be GC'd mid-flight
    app.state.sim = sim
    app.state.sim_task = asyncio.create_task(sim.run_async())
    yield
    app.state.sim_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await app.state.sim_task


def create_app() -> FastAPI:
    app = FastAPI(title="Virtual AHU", lifespan=lifespan)
    app.include_router(devices.router)
    app.include_router(objects.router)
    return app
