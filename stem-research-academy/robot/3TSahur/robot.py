"""3TSahur on MotionModule: mecanum drive plus the two-servo ramp.

MotionModule calls `create_drive(module)` once at startup and then `drive(...)`
for every Driver Station command. The same forward / strafe / rotate numbers
arrive from the keyboard, a game controller or a phone's touch sticks:

    forward  W / S    left stick Y
    strafe   D / A    left stick X
    rotate   Q / E    right stick X   (+rotate turns left)

`hardware.py` holds 3TSahur's own pins, `mixer.py` its tested wheel math and
`ramp.py` the GPIO ramp servos. The Driver Station's Open ramp, Close ramp and
Toggle ramp buttons (and the R key, set in dashboard.py) call `control()`.
"""

from mixer import WHEELS, outputs
from ramp import Ramp


class SahurDrive:
    def __init__(self, module, ramp=None):
        self.module = module
        self.ramp = ramp if ramp is not None else Ramp(module.hardware)

    def drive(self, forward, strafe, rotate, speed=0.5):
        """Called by the Driver Station. `speed` is the 0.0-1.0 power limit."""

        powers = outputs(forward, strafe, rotate, speed)
        self.module.set_motors(powers)
        return {"outputs": powers}

    def stop(self):
        """Called whenever control stops. The ramp keeps holding its position."""

        self.module.set_motors({name: 0 for name in WHEELS})

    def controls(self):
        return [
            {"name": "toggle_ramp", "label": "Toggle ramp", "kind": "button",
             "detail": f"Ramp is {self.ramp.state}. Opens to 120° or closes to 0° (R)"},
            {"name": "open_ramp", "label": "Open ramp", "kind": "button",
             "detail": "Both servos to 120°"},
            {"name": "close_ramp", "label": "Close ramp", "kind": "button",
             "detail": "Both servos to 0°"},
        ]

    def control(self, name, value):
        if name == "toggle_ramp":
            return {"ramp": self.ramp.toggle()}
        if name == "open_ramp":
            return {"ramp": self.ramp.set_state("open")}
        if name == "close_ramp":
            return {"ramp": self.ramp.set_state("closed")}
        raise ValueError(f"Unknown control: {name}")


def create_drive(module):
    """Required entry point."""

    return SahurDrive(module)
