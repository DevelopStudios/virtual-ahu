"""Centralised configuration for the virtual AHU.

Values are read from environment variables prefixed with ``AHU_``.
If a variable is missing the default is used.
"""
class Settings:
    """Simple settings container with defaults."""
    def __init__(self):
        self.port = 8000
        self.tick_rate = 1.0
        self.speed_factor = 1.0
    #Port on which the FastAPI server will listen
    port: int = 8000

    #Seconds per simulation step (tick) 1.0 = real-time second.
    tick_rate: float = 1.0

    #Speed factor - >1 runs faster that wall-clock, <1 slower.
    speed_factor: float = 1.0

    class Config:
        env_prefix = "AHU_"