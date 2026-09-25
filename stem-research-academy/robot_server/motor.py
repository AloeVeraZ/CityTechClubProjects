"""One two-input H-bridge motor port (the MotionModule motor channel)."""

from __future__ import annotations

from .hardware import MotorPort


class HBridgeMotor:
    """Drive one port by PWM on its forward or reverse input, never both.

    ``inverted`` flips which input a positive command drives. It is the only
    fix for a wheel that turns the wrong way: never move a wire or change the
    drive math. The Debug page changes it at runtime.
    """

    def __init__(self, gpio, port: MotorPort, frequency: int, inverted: bool = False) -> None:
        self.gpio = gpio
        self.port = port
        self.frequency = frequency
        self.inverted = bool(inverted)
        self.value = 0.0
        self._electrical_direction = 0
        gpio.claim_output(port.forward_gpio)
        gpio.claim_output(port.reverse_gpio)
        self._off()

    def electrical_value(self, logical_value: float) -> float:
        value = max(-1.0, min(1.0, float(logical_value)))
        return -value if self.inverted else value

    def would_reverse(self, logical_value: float) -> bool:
        value = self.electrical_value(logical_value)
        direction = 1 if value > 0 else -1 if value < 0 else 0
        return bool(direction and self._electrical_direction and direction != self._electrical_direction)

    def set(self, logical_value: float) -> None:
        value = self.electrical_value(logical_value)
        duty = abs(value) * 100.0
        if value > 0:
            self.gpio.pwm(self.port.reverse_gpio, self.frequency, 0)
            self.gpio.write(self.port.reverse_gpio, False)
            self.gpio.pwm(self.port.forward_gpio, self.frequency, duty)
            self._electrical_direction = 1
        elif value < 0:
            self.gpio.pwm(self.port.forward_gpio, self.frequency, 0)
            self.gpio.write(self.port.forward_gpio, False)
            self.gpio.pwm(self.port.reverse_gpio, self.frequency, duty)
            self._electrical_direction = -1
        else:
            self._off()
            self._electrical_direction = 0
        self.value = max(-1.0, min(1.0, float(logical_value)))

    def _off(self) -> None:
        for gpio in (self.port.forward_gpio, self.port.reverse_gpio):
            self.gpio.pwm(gpio, self.frequency, 0)
            self.gpio.write(gpio, False)

    def close(self) -> None:
        self.set(0)
