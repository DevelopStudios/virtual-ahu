# Virtual AHU

A FastAPI web app simulating one air-handling unit (AHU-1) serving one zone,
exposing its points through a REST API that mimics the **BACnet object
model** — objects, properties, priority arrays, COV — without the BACnet
wire protocol.

A PID loop cools the zone against occupant heat load and outdoor weather;
every value flows through a point registry that the API reads and writes,
so a manual override at priority 8 genuinely changes the physics.

**Live deployment:** https://virtual-ahu-m820f.sevalla.app
(interactive docs at [/docs](https://virtual-ahu-m820f.sevalla.app/docs))

## Quick start (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                          # 25 tests
python -m app.sim.engine           # watch the sim in a terminal
uvicorn app.main:create_app --factory --port 8000
```

---

# API reference

Base URLs:

| Environment | REST | WebSocket |
| ----------- | ---- | --------- |
| Local       | `http://localhost:8000` | `ws://localhost:8000/cov` |
| Production  | `https://virtual-ahu-m820f.sevalla.app` | `wss://virtual-ahu-m820f.sevalla.app/cov` |

OpenAPI/Swagger UI at `/docs`, machine-readable schema at `/openapi.json`
(covers all HTTP routes; the WebSocket is documented below only).
CORS: the app allows any origin (`Access-Control-Allow-Origin: *`), so a
browser frontend can call both local and production APIs directly.

Objects are addressed as `{type}/{instance}` where `type` is one of
`analog-input`, `analog-value`, `analog-output`, `binary-input`,
`binary-output`, `binary-value`.

## Discovery

### `GET /devices`

The Who-Is/I-Am stand-in. Returns every device and its point list
(identity only — values are read per property, see below).

```json
[
  {
    "device-instance": 1001,
    "object-name": "AHU-1",
    "objects": [
      {"type": "analog-input", "instance": 1, "name": "AHU1-ZN-T"},
      ...
    ]
  }
]
```

### `GET /objects`

Flat list of all objects: `[{"type", "instance", "name"}, ...]`.

## ReadProperty

### `GET /objects/{type}/{instance}/properties/{property}`

Returns `{"value": <any>}`. `404` for unknown object or property, or a
property the object doesn't carry (e.g. `priority-array` on a sensor).

Valid `property` names:

| Property             | On which objects   | Value shape                          |
| -------------------- | ------------------ | ------------------------------------ |
| `present-value`      | all                | number (binaries use 0/1)            |
| `object-name`        | all                | string                               |
| `units`              | all                | string or null                       |
| `status-flags`       | all                | `{"in-alarm": bool, "fault": bool, "overridden": bool, "out-of-service": bool}` |
| `out-of-service`     | all                | bool                                 |
| `priority-array`     | AO/BO only         | array of 16 (number or null), index 0 = priority 1 |
| `relinquish-default` | AO/BO only         | number                               |

## WriteProperty

### `POST /objects/{type}/{instance}/properties/present-value`

Body: `{"value": <number|bool|null>, "priority": <1-16, optional>}`.
Returns the resulting `{"value": ...}` (i.e. the new present-value after
priority arbitration — may differ from what you wrote if a higher
priority is active).

Rules by object type:

- **Commandable (AO/BO)** — `priority` is **required**. `"value": null`
  relinquishes that priority slot (faithful BACnet: relinquish = write
  NULL). Convention: operator overrides at **8**, the PID loop owns **16**.
  Lower number wins.
- **Writable (AV/BV)** — plain write, **no** `priority` field.
- **Sensors (AI/BI)** — read-only, always `403`.

Errors: `404` unknown object; `403` read-only point or non-`present-value`
property; `422` missing/out-of-range priority or wrong value type.

Example — override the cooling valve, then release it:

```bash
POST /objects/analog-output/1/properties/present-value  {"value": 100, "priority": 8}
POST /objects/analog-output/1/properties/present-value  {"value": null, "priority": 8}
```

## Trends

### `GET /trends/{type}/{instance}?limit=100`

Newest-first history samples for one point (sampled every
`AHU_TREND_INTERVAL` sim-seconds into SQLite).

```json
{"point": "AHU1-ZN-T", "samples": [{"ts": 1783954190.07, "value": 20.96}, ...]}
```

`ts` is a Unix epoch float. `404` for unknown objects. **Note:** history
is ephemeral on the PaaS — it resets on every deploy/restart.

## Alarms

### `GET /alarms`

All alarms, oldest first. States: `active-unacked` → `active-acked` →
`cleared` (an alarm can also clear while unacked). While active, the
zone-temp point's `status-flags.in-alarm` is true.

```json
[{"id": 1, "point": "AHU1-ZN-T",
  "message": "high zone temp: 27.0 °C > 26.0 °C limit",
  "raised_at": 1783902078.05, "state": "active-unacked", "cleared_at": null}]
```

### `POST /alarms/{id}/ack`

Acknowledges (no body). Returns the updated alarm; `404` unknown id.
Acking a cleared alarm is a no-op that returns it unchanged.

To trip the alarm on demand: override the fan off
(`POST /objects/binary-output/1/properties/present-value` with
`{"value": 0, "priority": 8}`) — occupant heat load drives the zone past
the limit in a few sim-minutes. Release the fan and it clears itself.

## COV (Change-of-Value) — WebSocket

### `WS /cov`

1. Connect (`ws://` local, `wss://` production).
2. Send one subscription message:
   ```json
   {"subscribe": ["analog-input/1", "analog-output/1"]}
   ```
3. Receive an immediate snapshot of each subscribed point, then a push
   whenever a present-value changes by **≥ 0.1** (the COV increment):
   ```json
   {"object": "analog-output/1", "name": "AHU1-CLG-V", "value": 88.0, "ts": 1783955368.59}
   ```

Notes for frontend work: one subscription message per connection
(reconnect to change the set); unknown addresses are silently ignored;
no pings required. Quiet periods are normal — steady-state values inside
the increment don't push. Browser example:

```js
const ws = new WebSocket("wss://virtual-ahu-m820f.sevalla.app/cov");
ws.onopen = () => ws.send(JSON.stringify({subscribe: ["analog-input/1", "analog-output/1"]}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

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
var is honored, and pushes to `master` auto-deploy. **The SQLite trend
history is ephemeral** — the container filesystem is wiped on every
redeploy/restart. Point `AHU_DB_PATH` at a mounted volume if you need
trends to survive.

```bash
docker build -t virtual-ahu .
docker run -p 8000:8000 virtual-ahu
```
