"""Driver Station layout for 3TSahur: camera, ramp status, keys and sticks.

MotionModule loads this automatically because it sits beside robot.py. The
Logitech USB camera is streamed by MotionModule itself; nothing here has to
open it.
"""

from motion_module.telemetry import CameraFeed, IMUReading, TelemetryDashboard


class SahurDashboard(TelemetryDashboard):
    def __init__(self, module, drive):
        self.module = module
        self.drive = drive
        self.ramp = getattr(drive, "ramp", None)

    def driver_bindings(self):
        # W/S drive, A/D strafe, Q/E turn and space stop are the defaults.
        # R presses robot.py's Toggle ramp button, as on the original dashboard.
        return {"toggle_ramp": "r"}

    def gamepad_buttons(self):
        return {"y": "toggle_ramp"}

    def touch_panels(self):
        # The ramp status and buttons on a phone or tablet too.
        return ["mechanisms", "pi_inputs"]

    def cameras(self):
        # Blank URL: MotionModule streams the USB camera plugged into the Pi.
        return [CameraFeed("Front camera", "", connected=False, detail="Logitech USB camera")]

    def imu(self):
        return IMUReading(
            name="IMU", connected=False, calibrated=False,
            detail="3TSahur has no IMU. GPIO18 drives ramp servo 2, so the IMU bus stays off.",
        )

    def pi_inputs(self):
        return [self.ramp.reading()] if self.ramp is not None else []

    def close(self):
        """MotionModule calls this when the service stops or a project is deployed."""

        if self.ramp is not None:
            self.ramp.shutdown()


def create_dashboard(module, drive):
    return SahurDashboard(module, drive)
