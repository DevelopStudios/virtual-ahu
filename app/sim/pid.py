"""Simple PID (or PI) controller used by the AHU simulation.

The controller is deliberately tiny - it only needs:
* a method that receives the current measured value,
* the elapsed time step,
* and returns a command that will be added to the set-point
  (so the caller can enforce any temperature limits it wants).

All math is done in plain Python; no external deps are required.
"""

class PID:
    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float = 0.0,
        setpoint: float = 0.0,
        output_limits: tuple[float, float] = (-100.00, 100.0)
    ):
        """
        Parameters
        ----------
        kp, ki, kd : float
            Proportional, integral and derivative gains.
        setpoint : float
            Desired target value (°C for our AHU).
        output_limits : (min, max)
            Clip the raw PID output to these limits.
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.min_out, self.max_out = output_limits
        self._integral = 0.0
        self._prev_error: float | None = None
    
    def update(self, measured: float, dt: float) -> float:
        """
        Compute a new command given the measured value and elapsed time.

        Returns a value clipped to ``output_limits``.
        """
        error = self.setpoint - measured
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if self._prev_error is not None else 0.0
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        self._prev_error = error
        return max(self.min_out, min(self.max_out, output))