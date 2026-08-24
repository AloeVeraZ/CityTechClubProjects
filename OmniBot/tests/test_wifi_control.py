import unittest

from wifi_control import RemoteControlState


class RemoteControlStateTests(unittest.TestCase):
    WALL_MS = 1_000_000

    @staticmethod
    def command(**overrides):
        command = {
            "session": "laptop-one",
            "sequence": 1,
            "expires_at_ms": RemoteControlStateTests.WALL_MS + 300,
            "forward": 1,
            "strafe": 0,
            "turn": 0,
        }
        command.update(overrides)
        return command

    def setUp(self):
        self.state = RemoteControlState(watchdog_seconds=0.30)

    def test_enable_then_accepts_current_drive_input(self):
        self.state.enable("laptop-one")
        result = self.state.submit(
            self.command(), wall_time_ms=self.WALL_MS, monotonic_time=10.0
        )

        self.assertTrue(result["ok"])
        snapshot = self.state.consume(10.1)
        self.assertTrue(snapshot.enabled)
        self.assertEqual(snapshot.forward, 1)

    def test_moving_command_watchdog_disables_and_zeros_input(self):
        enabled = self.state.enable("laptop-one")
        self.state.submit(
            self.command(), wall_time_ms=self.WALL_MS, monotonic_time=10.0
        )

        snapshot = self.state.consume(10.31)

        self.assertFalse(snapshot.enabled)
        self.assertEqual(snapshot.forward, 0)
        self.assertGreater(snapshot.generation, enabled["generation"])

    def test_expired_neutral_command_stays_enabled(self):
        self.state.enable("laptop-one")
        self.state.submit(
            self.command(forward=0),
            wall_time_ms=self.WALL_MS,
            monotonic_time=10.0,
        )

        snapshot = self.state.consume(10.31)

        self.assertTrue(snapshot.enabled)
        self.assertFalse(snapshot.moving)

    def test_stop_disables_immediately(self):
        self.state.enable("laptop-one")
        self.state.submit(
            self.command(), wall_time_ms=self.WALL_MS, monotonic_time=10.0
        )

        self.state.stop()

        snapshot = self.state.consume(10.01)
        self.assertFalse(snapshot.enabled)
        self.assertFalse(snapshot.moving)

    def test_stale_sequence_cannot_replace_newer_input(self):
        self.state.enable("laptop-one")
        self.state.submit(
            self.command(sequence=2, forward=0),
            wall_time_ms=self.WALL_MS,
            monotonic_time=10.0,
        )

        result = self.state.submit(
            self.command(sequence=1, forward=1),
            wall_time_ms=self.WALL_MS,
            monotonic_time=10.01,
        )

        self.assertTrue(result["stale"])
        self.assertEqual(self.state.consume(10.02).forward, 0)

    def test_other_session_cannot_take_over_without_enabling(self):
        self.state.enable("laptop-one")

        result = self.state.submit(
            self.command(session="laptop-two"),
            wall_time_ms=self.WALL_MS,
            monotonic_time=10.0,
        )

        self.assertTrue(result["session_mismatch"])
        self.assertFalse(self.state.consume(10.01).moving)

    def test_expired_or_implausibly_future_input_disables(self):
        for expires_at_ms in (self.WALL_MS - 1, self.WALL_MS + 1001):
            with self.subTest(expires_at_ms=expires_at_ms):
                self.state.enable("laptop-one")
                result = self.state.submit(
                    self.command(expires_at_ms=expires_at_ms),
                    wall_time_ms=self.WALL_MS,
                    monotonic_time=10.0,
                )
                self.assertTrue(result["expired"])
                self.assertFalse(self.state.consume(10.0).enabled)

    def test_non_finite_input_is_rejected(self):
        self.state.enable("laptop-one")
        with self.assertRaisesRegex(ValueError, "forward must be finite"):
            self.state.submit(
                self.command(forward="NaN"),
                wall_time_ms=self.WALL_MS,
                monotonic_time=10.0,
            )

    def test_runtime_telemetry_is_available_to_browser(self):
        self.state.report_runtime(
            enabled=True,
            armed=True,
            source="wifi",
            telemetry=["Motor 0: FWD"],
            servo="Servo 0: +0.0 deg",
        )

        status = self.state.public_status()

        self.assertEqual(status["source"], "wifi")
        self.assertEqual(status["telemetry"], ["Motor 0: FWD"])
        self.assertEqual(status["watchdog_ms"], 300)


if __name__ == "__main__":
    unittest.main()
