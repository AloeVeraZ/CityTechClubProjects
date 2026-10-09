"""Debug → Drive Test for 3TSahur, using the same mix as the Driver Station.

MotionModule's built-in Drive Test only runs on its reference wiring, so this
file gives the Debug page 3TSahur's own wiring and mix. W/S, D/A and Q/E keep
their fixed meanings; Space always stops every motor.
"""

from mixer import WHEELS, outputs


class SahurTestDrive:
    def __init__(self, module):
        self.module = module

    def drive(self, forward, strafe, rotate, speed=0.4):
        powers = outputs(forward, strafe, rotate, speed)
        self.module.set_motors(powers)
        return {"outputs": powers}

    def stop(self):
        self.module.set_motors({name: 0 for name in WHEELS})


def create_test(module):
    return SahurTestDrive(module)
