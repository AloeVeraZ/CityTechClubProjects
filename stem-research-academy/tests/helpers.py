import tempfile
from pathlib import Path

from robot_server.controller import MotionController
from robot_server.gpio import MockGPIO
from robot_server.imu import MockIMU
from robot_server.robot import Robot
from robot_server.servo import MockServoBoard
from robot_server.settings import SettingsStore


def make_robot(test_case):
    folder = tempfile.TemporaryDirectory()
    test_case.addCleanup(folder.cleanup)
    gpio = MockGPIO()
    controller = MotionController(gpio, MockServoBoard())
    robot = Robot(controller, MockIMU(), SettingsStore(Path(folder.name) / "robot.json"))
    test_case.addCleanup(robot.close)
    return robot, gpio
