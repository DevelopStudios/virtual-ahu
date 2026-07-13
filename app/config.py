"""Centralised configuration for the virtual AHU.

Values are read from environment variables prefixed with ``AHU_``;
missing variables fall back to the defaults below.
"""

import os


class Settings:
    def __init__(self):
        # Port on which the FastAPI server listens
        self.port: int = int(os.getenv("AHU_PORT", "8000"))
        # Simulation seconds per tick
        self.tick_rate: float = float(os.getenv("AHU_TICK_RATE", "1.0"))
        # >1 runs faster than wall-clock, <1 slower
        self.speed_factor: float = float(os.getenv("AHU_SPEED_FACTOR", "1.0"))
        # SQLite trend database (ephemeral on a PaaS — history since last boot)
        self.db_path: str = os.getenv("AHU_DB_PATH", "ahu_history.db")
        # Simulation seconds between trend samples
        self.trend_interval: float = float(os.getenv("AHU_TREND_INTERVAL", "5.0"))
        # High-zone-temp alarm threshold, °C
        self.high_temp_limit: float = float(os.getenv("AHU_HIGH_TEMP_LIMIT", "26.0"))
