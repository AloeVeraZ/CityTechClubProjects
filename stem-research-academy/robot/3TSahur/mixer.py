"""3TSahur's physically verified mecanum mix, in MotionModule's conventions.

MotionModule sends +forward for W, +strafe for D (right) and +rotate for Q
(left). The original 3TSahur dashboard sent +strafe for A, so strafe is
flipped once here. Everything after that is the original robot_server mix,
unchanged:

- The chassis' longitudinal axis is opposite the partner convention, so
  forward/backward is inverted while strafe and rotation keep their verified
  directions. W drives GPIO6, 16, 21 and 13.
- For Q the two front channels get +rotate and the two rear channels get
  -rotate. With the rear motor pins swapped in hardware.py this turns the
  robot about its center. E is the exact inverse.

Never move a pin to fix a direction. Change this mix or a motor's `inverted`
value in hardware.py instead.
"""

import math

WHEELS = ("front_left", "rear_left", "front_right", "rear_right")


def clamp(value, low=-1.0, high=1.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Drive commands must be numbers")
    if not math.isfinite(value):
        raise ValueError("Drive commands must be finite")
    return max(low, min(high, float(value)))


def mix(forward, strafe, rotate):
    """Normalized wheel powers by name; +strafe is right and +rotate turns left."""

    forward, strafe, rotate = clamp(forward), clamp(strafe), clamp(rotate)
    longitudinal = -forward
    lateral = -strafe  # the original dashboard's +strafe was A (left)
    wheels = {
        "front_left": longitudinal + lateral + rotate,
        "rear_left": longitudinal - lateral - rotate,
        "front_right": longitudinal - lateral + rotate,
        "rear_right": longitudinal + lateral - rotate,
    }
    scale = max(1.0, *(abs(power) for power in wheels.values()))
    return {name: power / scale for name, power in wheels.items()}


def outputs(forward, strafe, rotate, speed):
    """Wheel powers scaled by the Driver Station's 0.0-1.0 speed limit."""

    limit = clamp(speed, 0.0, 1.0)
    return {name: power * limit for name, power in mix(forward, strafe, rotate).items()}
