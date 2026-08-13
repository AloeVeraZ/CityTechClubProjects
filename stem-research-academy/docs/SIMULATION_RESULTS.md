# Simulation results

Date: 2026-08-12

The integration base and the 3TSahur/LARP updates were compiled with Python.
All 78 hardware-independent target tests passed in an isolated desktop virtual
environment. The partner repository was also tested independently from its own
working directory: all 32 of its tests passed.

| Group | Checks | Result |
| --- | ---: | --- |
| `test_dashboard_ui.py` | three visible camera-left/control-right workspaces, one/two/three-feed camera selection with safe fallback, CSI, vision/landmark controls, bottom mission tools, automatic camera display, and lightweight UI guards | pass |
| `test_motor.py` | mecanum mixing, normalization, reversal dead-time, confirmed GPIO/PWM mapping, and redundant-heartbeat write suppression | pass |
| `test_camera.py` | Logitech V4L2 discovery ordering/model naming, automatic reconnect supervision, and compatibility profile restart | pass |
| `test_recon_features.py` | static-scene inference gating, periodic forced inference, evidence JPEG/JSON pairing, and cached health snapshots | pass |
| `test_firmware.py` | LARP reconnect behavior, CSI status fields, capped camera stream rate, unchanged-output suppression, firmware settings, partner-config migration, hostname rollback, and installer invariants | pass |
| `test_scouts.py` | heartbeat registry handling | pass |
| `test_server.py` | hub API, expiry/sequence safety, partner environment aliases, profile/control isolation, health/evidence/landmark isolation, timeline, snapshot failure handling, dashboard, and scout proxy behavior | pass |
| `test_swarm_compatibility.py` | simultaneous 3TSahur, LARP A, and LARP B route compatibility plus local control-path queue check | pass |

The test harness uses fake GPIO/PWM implementations and mocked network/camera
interfaces. It verifies the installed PWM pairs, inverted longitudinal axis,
unchanged strafe/turn signs, and equal 75% output on all four motors for both
Q and E rotations.

The latency pass confirms that an unchanged held command performs zero
additional Pi PWM starts or duty-cycle changes. The LARP firmware similarly
refreshes `lastCommandAt` without repeating `drivetrain.drive`, and its 2 ms
disconnected loop sends a stop only on a state transition. Boot still forces a
physical zero command, and both watchdogs retain their existing timeouts.

## Control-path timing simulation

Using the Flask test client and simulated GPIO/network interfaces, 100 current
3TSahur drive commands averaged **0.131 ms** per request (95th percentile
**0.171 ms**, maximum **1.562 ms**). One hundred immediate LARP proxy commands
averaged **0.125 ms** (95th percentile **0.166 ms**, maximum **0.273 ms**).

This confirms the dashboard/API control path does not contain a multi-second
software queue. It does not measure physical motor response or real radio
latency. The dashboard's one-active-camera policy and the ESP32-CAM 10 FPS cap
are intended to prevent the prior hotspot video congestion from delaying those
small command packets.

The compatibility API test also ran a camera-profile update immediately
followed by a current drive command. Both passed in simulation. The operator UI
does not expose profile choices; it reports one automatic camera mode.

## Three-robot compatibility and timing check

The current compatibility pass registered both LARPs with distinct simulated
hotspot addresses, then sent one current 3TSahur mecanum command, one LARP A
drive command, and one LARP B drive command. Both LARP status routes returned
successfully and the 3TSahur motor state remained current. This exercises the
same dashboard API routes that the three workspaces use, with scout HTTP calls mocked
to remove physical radio variation.

After the reconnaissance-efficiency additions, three runs of 1,000 repeated composite cycles,
each containing one current 3TSahur command and one command for each LARP,
averaged **1.529-1.742 ms** per cycle, with **2.284-2.826 ms** 95th-percentile
times and a **15.949 ms** worst observed maximum on the Windows desktop
validation host. The current one-page UI pass produced **2.094 ms** average,
**3.371 ms** p95, and **15.708 ms** maximum for another 1,000-cycle run. The
compatibility test also asserts a 50 ms local ceiling across repeated Pi/LARP
requests, so a new local request queue cannot silently reintroduce multi-second
delays.

Re-run that timing simulation from the project directory with:

```bash
python tests/benchmark_control_paths.py --cycles 1000
```

The optional reconnaissance additions do not alter drive/stop route logic,
control timer rates, motor mixing, watchdog timeouts, or network settings.
Analysis is disabled by default and pauses during motion; health collection and
evidence writes run on bounded background workers; the browser drops auxiliary
polls while driving and suspends video only after measured degradation.

This confirms software compatibility and the absence of a local API backlog;
it does **not** measure the Pi's hotspot airtime, 2.4 GHz interference, camera
processing, servo behavior, battery voltage drop, or actual motor response.
Use [the field information checklist](FIELD_INFORMATION_CHECKLIST.md) and the
raised-wheel connection test before declaring the system field-ready.

Not simulated: physical motor direction/current, C270 USB capture, real Wi-Fi
radio behavior, or external camera hardware. Those require the actual hardware
and must be performed using the raised-wheel procedure in the setup guide.
