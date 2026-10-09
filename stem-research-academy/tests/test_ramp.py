"""The GPIO ramp servos, with a stand-in for the pigpio daemon."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "robot" / "3TSahur"))

from ramp import Ramp, pulse_width  # noqa: E402


class FakePigpio:
    OUTPUT = 1

    def __init__(self, connected=True):
        self.client = FakePi(connected)

    def pi(self):
        return self.client


class FakePi:
    def __init__(self, connected):
        self.connected = connected
        self.modes = {}
        self.pulses = {}
        self.writes = 0
        self.stopped = False

    def set_mode(self, gpio, mode):
        self.modes[gpio] = mode
        return 0

    def set_servo_pulsewidth(self, gpio, pulse):
        self.pulses[gpio] = pulse
        self.writes += 1
        return 0

    def stop(self):
        self.stopped = True


class RampTests(unittest.TestCase):
    def test_pulse_widths_match_the_original_mirrored_servos(self):
        self.assertEqual((pulse_width(0, 0), pulse_width(1, 0)), (1000, 1667))
        self.assertEqual((pulse_width(0, 120), pulse_width(1, 120)), (1667, 1000))

    def test_startup_holds_both_servos_closed(self):
        pigpio = FakePigpio()
        ramp = Ramp(True, pigpio_module=pigpio)
        self.assertTrue(ramp.hardware)
        self.assertEqual(pigpio.client.modes, {12: 1, 18: 1})
        self.assertEqual(pigpio.client.pulses, {12: 1000, 18: 1667})
        self.assertEqual(ramp.state, "closed")

    def test_open_close_and_toggle(self):
        pigpio = FakePigpio()
        ramp = Ramp(True, pigpio_module=pigpio)
        self.assertEqual(ramp.set_state("open"), "open")
        self.assertEqual(pigpio.client.pulses, {12: 1667, 18: 1000})
        self.assertEqual(ramp.toggle(), "closed")
        self.assertEqual(pigpio.client.pulses, {12: 1000, 18: 1667})

    def test_repeated_commands_do_not_rewrite_pulses(self):
        pigpio = FakePigpio()
        ramp = Ramp(True, pigpio_module=pigpio)
        writes = pigpio.client.writes
        ramp.set_state("closed")
        self.assertEqual(pigpio.client.writes, writes)

    def test_missing_pigpiod_is_reported_and_refused(self):
        ramp = Ramp(True, pigpio_module=FakePigpio(connected=False))
        self.assertFalse(ramp.available)
        self.assertIn("pigpiod", ramp.error)
        self.assertEqual(ramp.reading()["status"], "error")
        with self.assertRaises(ValueError):
            ramp.set_state("open")

    def test_unknown_state_is_refused(self):
        with self.assertRaises(ValueError):
            Ramp(False).set_state("half")

    def test_simulation_tracks_state_without_pigpio(self):
        ramp = Ramp(False)
        self.assertTrue(ramp.available)
        self.assertEqual(ramp.toggle(), "open")
        self.assertEqual(ramp.reading()["value"], "open")

    def test_shutdown_stops_the_pulses(self):
        pigpio = FakePigpio()
        ramp = Ramp(True, pigpio_module=pigpio)
        ramp.shutdown()
        self.assertEqual(pigpio.client.pulses, {12: 0, 18: 0})
        self.assertTrue(pigpio.client.stopped)
        ramp.shutdown()  # safe to call twice


if __name__ == "__main__":
    unittest.main()
