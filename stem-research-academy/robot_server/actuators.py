"""Direct Raspberry Pi GPIO control for the two-position 3TSahur ramp."""

from __future__ import annotations

import os
import threading


class DirectGPIOServoBoard:
    """Drive two hobby servos directly with 50 Hz RPi.GPIO software PWM."""

    CLOSED_ANGLE = 0.0
    OPEN_ANGLE = 30.0

    def __init__(self, gpio_module=None) -> None:
        self.frequency = int(os.environ.get("RAMP_SERVO_FREQUENCY_HZ", "50"))
        self.minimum_us = int(os.environ.get("RAMP_SERVO_MIN_PULSE_US", "1000"))
        self.maximum_us = int(os.environ.get("RAMP_SERVO_MAX_PULSE_US", "2000"))
        self.settle_seconds = float(os.environ.get("RAMP_SERVO_SETTLE_SECONDS", "0.6"))
        self.pins = {
            0: int(os.environ.get("RAMP_SERVO_0_GPIO_BCM", "12")),
            1: int(os.environ.get("RAMP_SERVO_1_GPIO_BCM", "18")),
        }
        self.hardware = False
        self.error: str | None = None
        self._gpio = gpio_module
        self._pwms: dict[int, object] = {}
        self._detach_timers: dict[int, threading.Timer] = {}
        self._lock = threading.Lock()

        try:
            if self._gpio is None:
                import RPi.GPIO as GPIO  # type: ignore

                self._gpio = GPIO
            self._validate_configuration()
            self._gpio.setwarnings(False)
            self._gpio.setmode(self._gpio.BCM)
            for channel, pin in self.pins.items():
                self._gpio.setup(pin, self._gpio.OUT, initial=self._gpio.LOW)
                pwm = self._gpio.PWM(pin, self.frequency)
                pwm.start(self._duty_cycle(self.CLOSED_ANGLE))
                self._pwms[channel] = pwm
            self.hardware = True
            # Move both servos to zero at startup, then remove the continuously
            # varying Linux software-PWM signal so the servos cannot hunt.
            with self._lock:
                for channel in self._pwms:
                    self._schedule_detach_locked(channel)
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self.error = f"Direct servo GPIO unavailable: {error}"
            self.hardware = False
            self._stop_pwm()

    def _validate_configuration(self) -> None:
        if not 40 <= self.frequency <= 100:
            raise ValueError("RAMP_SERVO_FREQUENCY_HZ must be between 40 and 100")
        if not 400 <= self.minimum_us < self.maximum_us <= 3000:
            raise ValueError("Invalid ramp servo pulse-width range")
        if not 0.1 <= self.settle_seconds <= 5:
            raise ValueError("RAMP_SERVO_SETTLE_SECONDS must be between 0.1 and 5")
        if len(set(self.pins.values())) != 2:
            raise ValueError("Ramp servos must use two different GPIO pins")

    def _duty_cycle(self, angle: float) -> float:
        angle = max(0.0, min(180.0, float(angle)))
        pulse_us = self.minimum_us + (self.maximum_us - self.minimum_us) * angle / 180.0
        return pulse_us * self.frequency / 10_000.0

    def set_angle(self, channel: int, angle: float) -> None:
        with self._lock:
            if channel not in self._pwms:
                raise ValueError(f"Ramp servo channel {channel} is unavailable")
            timer = self._detach_timers.pop(channel, None)
            if timer is not None:
                timer.cancel()
            self._pwms[channel].ChangeDutyCycle(self._duty_cycle(angle))
            self._schedule_detach_locked(channel)

    def _schedule_detach_locked(self, channel: int) -> None:
        timer = threading.Timer(self.settle_seconds, self._detach_signal, args=(channel,))
        timer.daemon = True
        self._detach_timers[channel] = timer
        timer.start()

    def _detach_signal(self, channel: int) -> None:
        with self._lock:
            self._detach_timers.pop(channel, None)
            pwm = self._pwms.get(channel)
            if pwm is not None:
                try:
                    pwm.ChangeDutyCycle(0)
                except RuntimeError:
                    pass

    def _stop_pwm(self) -> None:
        for timer in list(self._detach_timers.values()):
            timer.cancel()
        self._detach_timers.clear()
        for pwm in list(self._pwms.values()):
            try:
                pwm.ChangeDutyCycle(0)
                pwm.stop()
            except (AttributeError, RuntimeError):
                pass
        self._pwms.clear()

    def close(self) -> None:
        self._stop_pwm()
        if self._gpio is not None:
            try:
                self._gpio.cleanup(tuple(self.pins.values()))
            except (AttributeError, RuntimeError):
                pass


class ActuatorController:
    """Move both ramp servos between closed at 0° and open at 30°."""

    RAMP_STATES = {"open", "closed"}
    CLOSED_ANGLE = DirectGPIOServoBoard.CLOSED_ANGLE
    OPEN_ANGLE = DirectGPIOServoBoard.OPEN_ANGLE

    def __init__(self, board: DirectGPIOServoBoard | None = None) -> None:
        self._lock = threading.Lock()
        self._board = board or DirectGPIOServoBoard()
        self._ramp = "closed"
        self._channel_angles = {0: self.CLOSED_ANGLE, 1: self.CLOSED_ANGLE}

    def snapshot(self) -> dict:
        with self._lock:
            configured = self._board.hardware
            return {
                "configured": configured,
                "hardware": configured,
                "reason": self._board.error or "Direct GPIO ramp servos ready",
                "gpio_bcm": {str(channel): pin for channel, pin in self._board.pins.items()},
                "signal_release_seconds": getattr(self._board, "settle_seconds", 0.6),
                "channels": {str(channel): angle for channel, angle in self._channel_angles.items()},
                "ramp": {
                    "state": self._ramp,
                    "closed_angle": self.CLOSED_ANGLE,
                    "open_angle": self.OPEN_ANGLE,
                },
            }

    def set_ramp(self, state: object) -> dict:
        state_value = str(state).lower()
        if state_value not in self.RAMP_STATES:
            raise ValueError("Ramp state must be 'open' or 'closed'")
        target_angle = self.OPEN_ANGLE if state_value == "open" else self.CLOSED_ANGLE
        if self._board.hardware:
            try:
                self._board.set_angle(0, target_angle)
                self._board.set_angle(1, target_angle)
            except (OSError, RuntimeError, ValueError) as error:
                self._board.error = f"Ramp movement failed: {error}"
                self._board.hardware = False
        with self._lock:
            self._ramp = state_value
            self._channel_angles = {0: target_angle, 1: target_angle}
        return self.snapshot()

    def close(self) -> None:
        self._board.close()
