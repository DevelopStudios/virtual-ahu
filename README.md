# Virtual AHU

A lightweight Python simulation of a single air‑handling unit (AHU) zone.

## Overview
- **`engine.py`** runs a simple simulation loop that steps a `Zone` model using an outdoor temperature sine wave.
- **`zone.py`** implements a first‑order thermal model.
- **`weather.py`** provides a 24‑hour sinusoidal outdoor temperature.
- **`config.py`** supplies minimal configurable settings (port, tick rate, speed factor).

## Quick start
```bash
# (optional) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies (none beyond the standard library for the core demo)
# If you need pydantic-settings, install it or use the simple Settings class provided.

# Run the simulation (defaults to 10 ticks for a quick sanity check)
python3 engine.py
```

The script prints a one‑line status line each tick, e.g.:
```
[t=   0.0s] zone=21.98°C outdoor=15.00°C supply=15.00°C
```

## Extending the project
- Replace the placeholder `supply_temp = oa` with a PID controller to regulate zone temperature.
- Hook the loop into a FastAPI server (see the placeholder comment in `engine.py`).
- Add unit tests for `Zone.step` and `weather.outdoor_temp`.

## License
MIT (see `LICENSE` if added).
