# Virtual AHU

A FastAPI web app simulating one air-handling unit (AHU-1) serving one zone,
exposing its points through a REST API that mimics the **BACnet object
model** — objects, properties, priority arrays, COV — without the BACnet
wire protocol.

A PID loop cools the zone against occupant heat load and outdoor weather;
every value flows through a point registry that the API reads and writes,
so a manual override at priority 8 genuinely changes the physics.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                          # 25 tests
python -m app.sim.engine           # watch the sim in a terminal
uvicorn app.main:create_app --factory --port 8000
```

Then open http://localhost:8000/docs.

## API tour

```bash
# Discovery (Who-Is/I-Am stand-in)
curl localhost:8000/devices

# ReadProperty
curl localhost:8000/objects/analog-input/1/properties/present-value

# WriteProperty: operator override at priority 8 (beats the PID at 16)
curl -X POST localhost:8000/objects/analog-output/1/properties/present-value \
     -H 'Content-Type: application/json' -d '{"value": 100, "priority": 8}'

# Relinquish = write null at that priority
curl -X POST localhost:8000/objects/analog-output/1/properties/present-value \
     -H 'Content-Type: application/json' -d '{"value": null, "priority": 8}'

# Trends and alarms
curl localhost:8000/trends/analog-input/1?limit=10
curl localhost:8000/alarms
curl -X POST localhost:8000/alarms/1/ack

# COV over WebSocket: connect to /cov, then send
#   {"subscribe": ["analog-input/1", "analog-output/1"]}
```

## Point list (AHU-1, device instance 1001)

| Point      | Object            | Role                                   |
| ---------- | ----------------- | -------------------------------------- |
| AHU1-ZN-T  | analog-input 1    | zone temperature                       |
| AHU1-SA-T  | analog-input 2    | supply air temperature                 |
| AHU1-OA-T  | analog-input 3    | outdoor temp (24 h sine wave)          |
| AHU1-ZN-SP | analog-value 1    | zone setpoint (writable)               |
| AHU1-CLG-V | analog-output 1   | cooling valve %, commandable (PID @16) |
| AHU1-SF-C  | binary-output 1   | supply fan command, commandable        |
| AHU1-SF-S  | binary-input 1    | supply fan status                      |
| AHU1-OCC   | binary-value 1    | occupancy (writable; drives heat load) |

## Configuration (env vars)

| Variable              | Default          | Meaning                            |
| --------------------- | ---------------- | ---------------------------------- |
| `PORT` / `AHU_PORT`   | 8000             | listen port (PaaS injects `PORT`)  |
| `AHU_TICK_RATE`       | 1.0              | simulation seconds per tick        |
| `AHU_SPEED_FACTOR`    | 1.0              | >1 runs faster than wall-clock     |
| `AHU_DB_PATH`         | ahu_history.db   | SQLite trend database              |
| `AHU_TREND_INTERVAL`  | 5.0              | sim-seconds between trend samples  |
| `AHU_HIGH_TEMP_LIMIT` | 26.0             | high-zone-temp alarm threshold, °C |

## Deploy (Sevalla or any container PaaS)

The `Dockerfile` builds a self-contained image; the platform's `PORT` env
var is honored. **The SQLite trend history is ephemeral** — a container
filesystem is wiped on every redeploy/restart, so trends are "history
since last boot." Point `AHU_DB_PATH` at a mounted volume if you need
them to survive.

```bash
docker build -t virtual-ahu .
docker run -p 8000:8000 virtual-ahu
```
