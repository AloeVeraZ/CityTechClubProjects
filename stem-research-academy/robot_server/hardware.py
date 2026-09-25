"""Fixed 3TSahur wiring on the MotionModule harness.

3TSahur is purpose-built, so nothing here is chosen in the browser: the robot
uses exactly two dual H-bridge boards (MotionModule Drivers 1 and 2, four motor
ports), one PCA9685 servo board, and one BNO055 IMU. The pins are the locked
MotionModule reference wiring for those parts; MotionModule's Drivers 3 and 4
are not fitted on this robot.

What *can* change at runtime is which motor port drives which wheel, which
wheel is inverted, and which servo channel drives which half of the ramp. That
lives in ``settings.py`` and is edited from the Debug page, never here.

Software uses BCM GPIO numbers. The comments give physical header pins.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotorPort:
    port: int
    driver: int
    output: str
    forward_gpio: int
    reverse_gpio: int
    ground_physical: int

    @property
    def label(self) -> str:
        return f"Driver {self.driver} · {self.output}"


# Motor control ----------------------------------------------------------------
PWM_HZ = 1000        # PWM frequency sent to the H-bridge inputs
DEADTIME_MS = 15     # coast time inserted before any motor reverses
WATCHDOG_MS = 500    # every motor stops if no command arrives in time

# Each driver's control header reads IN1 IN2 IN3 IN4 GND. IN1/IN2 drive output
# A, IN3/IN4 drive output B. The forward wire is the first input of each pair.
#
#  port  driver · output  forward (IN1/IN3)  reverse (IN2/IN4)  driver ground
#  ----  ---------------  -----------------  -----------------  -------------
#    1   Driver 1 · A     pin 37 / GPIO26    pin 35 / GPIO19    pin 39
#    2   Driver 1 · B     pin 33 / GPIO13    pin 31 / GPIO6     pin 39
#    3   Driver 2 · A     pin 40 / GPIO21    pin 38 / GPIO20    pin 34
#    4   Driver 2 · B     pin 36 / GPIO16    pin 32 / GPIO12    pin 34
MOTOR_PORTS: dict[int, MotorPort] = {
    1: MotorPort(1, 1, "A", 26, 19, 39),
    2: MotorPort(2, 1, "B", 13, 6, 39),
    3: MotorPort(3, 2, "A", 21, 20, 34),
    4: MotorPort(4, 2, "B", 16, 12, 34),
}

# Servo board (PCA9685) ---------------------------------------------------------
#   pin 1 / 3.3 V -> VCC   pin 3 / GPIO2 -> SDA   pin 5 / GPIO3 -> SCL
#   pin 7 / GPIO4 -> OE    pin 9 / GND   -> GND
# Servo V+ comes from its own regulated 5-6 V supply, never from the Pi.
SERVO_I2C_BUS = 1
SERVO_ADDRESS = 0x40
SERVO_FREQUENCY_HZ = 50
SERVO_OE_GPIO = 4
SERVO_MIN_PULSE_US = 500
SERVO_MAX_PULSE_US = 2500
SERVO_CHANNELS = 16

# IMU (BNO055) -------------------------------------------------------------------
# Shares the servo board's I2C bus: VIN to 3.3 V (pin 17), GND to pin 6,
# SDA/SCL chained from the PCA9685's side header. ADR low = 0x28.
IMU_I2C_BUS = 1
IMU_ADDRESS = 0x28

WHEELS = ("front_left", "front_right", "rear_left", "rear_right")
WHEEL_LABELS = {
    "front_left": "Front left",
    "front_right": "Front right",
    "rear_left": "Rear left",
    "rear_right": "Rear right",
}
RAMP_SERVOS = ("ramp_left", "ramp_right")
RAMP_SERVO_LABELS = {"ramp_left": "Ramp servo A", "ramp_right": "Ramp servo B"}


PHYSICAL_BY_BCM = {
    2: 3, 3: 5, 4: 7, 5: 29, 6: 31, 7: 26, 8: 24, 9: 21, 10: 19, 11: 23,
    12: 32, 13: 33, 14: 8, 15: 10, 16: 36, 17: 11, 18: 12, 19: 35, 20: 38,
    21: 40, 22: 15, 23: 16, 24: 18, 25: 22, 26: 37, 27: 13, 0: 27, 1: 28,
}


def header_rows() -> list[dict]:
    """Every wired Pi header pin, in physical order, for the Debug wiring table."""

    rows: list[dict] = [
        {"physical": 1, "signal": "3.3 V", "to": "PCA9685 VCC (logic only)", "group": "servo"},
        {"physical": 3, "signal": "GPIO2 / SDA", "to": "PCA9685 SDA, BNO055 SDA", "group": "i2c"},
        {"physical": 5, "signal": "GPIO3 / SCL", "to": "PCA9685 SCL, BNO055 SCL", "group": "i2c"},
        {"physical": 6, "signal": "GND", "to": "BNO055 GND", "group": "imu"},
        {"physical": 7, "signal": f"GPIO{SERVO_OE_GPIO}", "to": "PCA9685 OE (active low)", "group": "servo"},
        {"physical": 9, "signal": "GND", "to": "PCA9685 GND", "group": "servo"},
        {"physical": 17, "signal": "3.3 V", "to": "BNO055 VIN", "group": "imu"},
    ]
    for item in MOTOR_PORTS.values():
        first, second = ("IN1", "IN2") if item.output == "A" else ("IN3", "IN4")
        rows.append({
            "physical": PHYSICAL_BY_BCM[item.forward_gpio],
            "signal": f"GPIO{item.forward_gpio}",
            "to": f"{item.label} {first} · port {item.port} forward",
            "group": "motor",
        })
        rows.append({
            "physical": PHYSICAL_BY_BCM[item.reverse_gpio],
            "signal": f"GPIO{item.reverse_gpio}",
            "to": f"{item.label} {second} · port {item.port} reverse",
            "group": "motor",
        })
    for driver, ground in sorted({(item.driver, item.ground_physical) for item in MOTOR_PORTS.values()}):
        rows.append({"physical": ground, "signal": "GND", "to": f"Driver {driver} GND (signal reference)", "group": "motor"})
    return sorted(rows, key=lambda row: row["physical"])


def port_rows() -> list[dict]:
    return [
        {
            "port": item.port,
            "driver": item.driver,
            "output": item.output,
            "label": item.label,
            "forward_gpio": item.forward_gpio,
            "forward_physical": PHYSICAL_BY_BCM[item.forward_gpio],
            "reverse_gpio": item.reverse_gpio,
            "reverse_physical": PHYSICAL_BY_BCM[item.reverse_gpio],
            "ground_physical": item.ground_physical,
        }
        for item in MOTOR_PORTS.values()
    ]
