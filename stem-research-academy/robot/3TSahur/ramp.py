"""The 3TSahur ramp: two GPIO servos held at closed (0°) or open (120°).

The servo signals come straight from the Pi header, timed by the pigpio
daemon (pigpiod.service, installed by the 3TSahur installer). pigpio keeps
sending the selected pulse continuously, so the ramp holds its position
without jitter while the drivetrain runs.

    Ramp Servo 1   BCM GPIO12, physical pin 32   normal direction
    Ramp Servo 2   BCM GPIO18, physical pin 12   mirrored in software

Both servos take +5 V and ground from the regulated buck converter, with the
buck ground tied to a Pi ground. Never connect a servo's 5 V wire to a GPIO.

In simulation (a laptop, or MOTIONMODULE_MOCK=1) nothing is opened and the
ramp state is only tracked.
"""

import threading

SERVO_GPIOS = {0: 12, 1: 18}
REVERSED = {1}
MINIMUM_PULSE_US = 1000
MAXIMUM_PULSE_US = 2000
CLOSED_ANGLE = 0.0
OPEN_ANGLE = 120.0
STATES = ("closed", "open")


def pulse_width(channel, logical_angle):
    """Microseconds for one servo; the mirrored servo counts down from 120°."""

    logical_angle = max(CLOSED_ANGLE, min(OPEN_ANGLE, float(logical_angle)))
    angle = OPEN_ANGLE - logical_angle if channel in REVERSED else logical_angle
    return round(MINIMUM_PULSE_US + (MAXIMUM_PULSE_US - MINIMUM_PULSE_US) * angle / 180.0)


class Ramp:
    def __init__(self, hardware, pigpio_module=None, pi_client=None):
        self.hardware = False
        self.simulated = not hardware
        self.error = ""
        self.state = "closed"
        self._lock = threading.Lock()
        self._pigpio = pigpio_module
        self._pi = pi_client
        self._held = {}
        if self.simulated:
            return
        try:
            if self._pigpio is None:
                import pigpio  # installed with pigpiod by the 3TSahur installer

                self._pigpio = pigpio
            if self._pi is None:
                self._pi = self._pigpio.pi()
            if not getattr(self._pi, "connected", False):
                raise OSError("pigpiod is not running (sudo systemctl start pigpiod)")
            for channel, gpio in SERVO_GPIOS.items():
                self._check(self._pi.set_mode(gpio, self._pigpio.OUTPUT), f"set GPIO{gpio} as an output")
                self._write(gpio, pulse_width(channel, CLOSED_ANGLE))
            self.hardware = True
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self.error = f"Ramp servos unavailable: {error}"
            self.shutdown()

    @staticmethod
    def _check(result, action):
        if isinstance(result, int) and result < 0:
            raise OSError(f"pigpio could not {action} (error {result})")

    def _write(self, gpio, pulse_us):
        if self._held.get(gpio) == pulse_us:
            return
        self._check(self._pi.set_servo_pulsewidth(gpio, pulse_us), f"set the GPIO{gpio} servo pulse")
        self._held[gpio] = pulse_us

    @property
    def available(self):
        return self.hardware or self.simulated

    def set_state(self, state):
        state = str(state).strip().lower()
        if state not in STATES:
            raise ValueError("The ramp state must be 'open' or 'closed'")
        with self._lock:
            if not self.available:
                raise ValueError(self.error or "The ramp servos are unavailable")
            if self.hardware:
                angle = OPEN_ANGLE if state == "open" else CLOSED_ANGLE
                try:
                    for channel, gpio in SERVO_GPIOS.items():
                        self._write(gpio, pulse_width(channel, angle))
                except (OSError, RuntimeError, ValueError) as error:
                    self.error = f"Ramp movement failed: {error}"
                    self.hardware = False
                    raise ValueError(self.error) from error
            self.state = state
            return state

    def toggle(self):
        return self.set_state("closed" if self.state == "open" else "open")

    def reading(self):
        """One line for the Driver Station's sensor panel."""

        if self.hardware:
            status, detail = "ok", "Held by pigpio on GPIO12 and GPIO18. R toggles."
        elif self.simulated:
            status, detail = "ok", "Simulated: no servos are driven on this computer."
        else:
            status, detail = "error", self.error
        return {
            "name": "Ramp",
            "value": self.state,
            "kind": "text",
            "channel": "GPIO12 + GPIO18",
            "connected": self.available,
            "status": status,
            "detail": detail,
        }

    def shutdown(self):
        """Stop the servo pulses and release pigpio. Called when the service stops."""

        with self._lock:
            pi, self._pi = self._pi, None
            self.hardware = False
            if pi is None:
                return
            for gpio in SERVO_GPIOS.values():
                try:
                    pi.set_servo_pulsewidth(gpio, 0)
                except (AttributeError, OSError, RuntimeError):
                    pass
            self._held.clear()
            try:
                pi.stop()
            except (AttributeError, OSError, RuntimeError):
                pass
