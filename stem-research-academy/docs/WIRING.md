# 3TSahur motor wiring

The 3TSahur mecanum chassis uses two DC 3–18 V, 10 A dual H-bridge motor
drivers. This table intentionally matches the partner repository's original
mecanum assignment. All numbers below are Raspberry Pi **BCM GPIO** numbers.

| Wheel | Driver input pair | Forward | Reverse |
| --- | --- | ---: | ---: |
| Front left | Driver 1 IN1 / IN2 | GPIO 5 | GPIO 6 |
| Rear left | Driver 1 IN3 / IN4 | GPIO 16 | GPIO 19 |
| Front right | Driver 2 IN1 / IN2 | GPIO 20 | GPIO 21 |
| Rear right | Driver 2 IN3 / IN4 | GPIO 13 | GPIO 26 |

This is encoded in `robot_server/motor.py` and tested in
`tests/test_motor.py`. Do not connect one GPIO to more than one driver input:
independent channels are required for mecanum strafe and rotation.

Before the first ground test, connect all logic and motor grounds, power motors
from their rated external supply, add a suitable fuse/power switch, and test
each direction with all wheels raised. If one wheel is physically reversed,
reverse only that motor's leads or swap only its `MotorPins` pair in code.

## Direct ramp-servo pinout

The two ramp servos use stable `pigpio`-timed signals from otherwise-unused Pi
GPIO pins. The code uses BCM numbering; the wiring table includes physical
header numbers so the connections are unambiguous.

| Servo | Wire | Raspberry Pi connection |
| --- | --- | --- |
| Ramp Servo 1 | Signal (orange/white/yellow) | BCM GPIO12, physical pin 32 |
| Ramp Servo 1 | +5 V (red) | Buck-converter +5 V output |
| Ramp Servo 1 | Ground (brown/black) | Buck-converter ground output |
| Ramp Servo 2 | Signal (orange/white/yellow) | BCM GPIO18, physical pin 12 |
| Ramp Servo 2 | +5 V (red) | Buck-converter +5 V output |
| Ramp Servo 2 | Ground (brown/black) | Buck-converter ground output |
| Common reference | Ground jumper | Buck-converter ground to Pi ground, physical pin 6 or 14 |

GPIO12 and GPIO18 carry 3.3 V control signals; never connect either servo's
red 5 V wire to a GPIO signal pin. Both servos start at logical 0 degrees, open
to 100 degrees, return to logical 0 degrees when closed, and continuously hold
the selected position. The physical-pin-12 servo is reversed in software so
closed pulls in and open pushes out; physical pin 32 retains its normal
direction.

The common-ground jumper is mandatory: without it, the 3.3 V servo signals do
not have a stable electrical reference and the servos can jitter unpredictably.
Set the buck converter to 5.0 V before connecting the servos and make sure its
continuous and peak current ratings cover both servos together.
