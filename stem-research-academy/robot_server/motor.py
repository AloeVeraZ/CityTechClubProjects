"""Fail-safe four-wheel mecanum drive control for Raspberry Pi GPIO."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class MotorPins:
    forward: int
    reverse: int


# BCM numbering. This is the only wheel-to-driver mapping that should need
# changing if the physical motor plugs do not match the assumed positions.
DEFAULT_MOTOR_PINS = {
    "front_left": MotorPins(5, 6),       # Driver 1, Motor A
    "rear_left": MotorPins(16, 19),      # Driver 1, Motor B
    "front_right": MotorPins(20, 21),    # Driver 2, Motor A
    "rear_right": MotorPins(13, 26),     # Driver 2, Motor B (wired reversed)
}


class _Motor:
    def __init__(self, gpio, pins: MotorPins, frequency: int) -> None:
        self.gpio = gpio
        self.pins = pins
        for pin in (pins.forward, pins.reverse):
            gpio.setup(pin, gpio.OUT, initial=gpio.LOW)
        self.forward_pwm = gpio.PWM(pins.forward, frequency)
        self.reverse_pwm = gpio.PWM(pins.reverse, frequency)
        self.forward_pwm.start(0)
        self.reverse_pwm.start(0)
        self._direction = 0

    def set(self, value: float) -> None:
        duty = min(100.0, abs(value) * 100.0)
        direction = 1 if value > 0 else -1 if value < 0 else 0
        if direction and self._direction and direction != self._direction:
            # Briefly remove power before reversing to protect the H-bridge.
            self.forward_pwm.ChangeDutyCycle(0)
            self.reverse_pwm.ChangeDutyCycle(0)
            time.sleep(0.015)
        if value > 0:
            self.reverse_pwm.ChangeDutyCycle(0)
            self.forward_pwm.ChangeDutyCycle(duty)
        elif value < 0:
            self.forward_pwm.ChangeDutyCycle(0)
            self.reverse_pwm.ChangeDutyCycle(duty)
        else:
            self.forward_pwm.ChangeDutyCycle(0)
            self.reverse_pwm.ChangeDutyCycle(0)
        self._direction = direction

    def close(self) -> None:
        self.set(0)
        self.forward_pwm.stop()
        self.reverse_pwm.stop()


class MecanumDrive:
    """Mix forward, strafe, and rotation commands into four wheel speeds."""

    def __init__(self, frequency: int = 1000, gpio_module=None) -> None:
        self._lock = threading.RLock()
        self._closed = False
        self.last_command = {"forward": 0.0, "strafe": 0.0, "rotate": 0.0, "speed": 0.75}
        self.is_hardware = False
        self._gpio = gpio_module
        self._motors: dict[str, _Motor] = {}

        if self._gpio is None:
            try:
                import RPi.GPIO as GPIO  # type: ignore

                self._gpio = GPIO
            except (ImportError, RuntimeError):
                self._gpio = None

        if self._gpio is not None:
            self._gpio.setwarnings(False)
            self._gpio.setmode(self._gpio.BCM)
            self._motors = {
                name: _Motor(self._gpio, pins, frequency)
                for name, pins in DEFAULT_MOTOR_PINS.items()
            }
            self.is_hardware = True

    @staticmethod
    def mix(forward: float, strafe: float, rotate: float) -> dict[str, float]:
        wheels = {
            "front_left": forward + strafe + rotate,
            "front_right": forward - strafe - rotate,
            "rear_left": forward - strafe + rotate,
            "rear_right": forward + strafe - rotate,
        }
        scale = max(1.0, *(abs(value) for value in wheels.values()))
        return {name: value / scale for name, value in wheels.items()}

    def drive(self, forward: float, strafe: float, rotate: float, speed: float = 0.75) -> None:
        with self._lock:
            if self._closed:
                return
            values = [forward, strafe, rotate, speed]
            if any(not isinstance(value, (int, float)) for value in values):
                raise ValueError("Drive values must be numbers")
            if any(not math.isfinite(float(value)) for value in values):
                raise ValueError("Drive values must be finite")
            forward, strafe, rotate = (
                max(-1.0, min(1.0, float(value)))
                for value in (forward, strafe, rotate)
            )
            speed = max(0.0, min(1.0, float(speed)))
            mixed = self.mix(forward, strafe, rotate)
            for name, value in mixed.items():
                if name in self._motors:
                    self._motors[name].set(value * speed)
            self.last_command = {
                "forward": forward,
                "strafe": strafe,
                "rotate": rotate,
                "speed": speed,
            }

    def stop(self) -> None:
        self.drive(0, 0, 0, self.last_command["speed"])

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            for motor in self._motors.values():
                motor.close()
            if self._gpio is not None:
                for pins in DEFAULT_MOTOR_PINS.values():
                    self._gpio.output((pins.forward, pins.reverse), self._gpio.LOW)
                self._gpio.cleanup()
            self._closed = True
