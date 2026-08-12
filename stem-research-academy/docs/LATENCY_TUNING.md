# Latency and connection tuning

The dashboard is optimized for control freshness rather than guaranteed video
quality. A drive command is always more important than a status poll, CSI
update, snapshot, camera profile change, or vision result.

## Current software protections

| Layer | Tuning | Purpose |
| --- | --- | --- |
| Browser control channel | Latest command only; stale in-flight requests abort after 140 ms | Prevents an old input from building a request backlog. |
| 3TSahur mecanum | 80 ms keyboard heartbeat, unchanged-PWM suppression, and 200 ms watchdog | Refreshes safety timing without rewriting four identical PWM outputs. |
| LARP drive channel | 80 ms keyboard heartbeat, unchanged-output suppression, and 500 ms ECHO watchdog | Refreshes safety timing without repeating motor-controller writes. |
| LARP HTTP proxy | 120 ms outbound timeout by default | Fails an unreachable scout quickly instead of tying up the current control request. |
| Auxiliary browser traffic | Status, CSI, timeline, analysis, snapshots, and evidence yield while any robot moves | Makes reconnaissance tools best-effort rather than competing with drive packets. |
| Adaptive control priority | Browser keeps 20 command samples and pauses the selected MJPEG stream for 10 s only after a failure or p95 ≥100 ms | Reacts to real congestion without reducing normal video quality. |
| LARP Wi-Fi recovery | Staggered 1.8/2.2 s controller retry and 2.0/2.4 s camera retry | Reduces worst-case reconnect delay and avoids synchronized retry bursts. |
| Video | One selected feed only; ESP32-CAM capped at 10 FPS | Preserves airtime for controls. |
| Optional analysis | One daemon worker, static-scene motion gate, periodic forced refresh, and control-heartbeat pause | Keeps YOLO/ArUco work outside request and drive timing. |
| USB camera | Stale-frame reporting plus bounded reconnect backoff | Recovers from a C270 disconnect without restarting motor control. |
| Health/evidence | Slow host checks are cached; bounded JPEG/JSON writes use a background queue | Keeps subprocess and disk work out of Flask control routes. |

`SCOUT_REQUEST_TIMEOUT_SECONDS` can be adjusted in the Pi configuration, but
do not increase it casually: a larger value increases the time an unreachable
LARP can occupy an HTTP worker. Start with the 120 ms default.

## Test in this order

1. Start with the **Control Priority** C270 profile, YOLO off, no camera feed
   open, and a raised-wheel 3TSahur test.
2. Enable the C270 feed and repeat. Then enable only the active LARP camera
   tab and repeat each scout separately.
3. Record the latency for each change, along with RSSI and hotspot distance.
4. If delay returns, turn off YOLO, keep one stream active, inspect the Pi
   power supply, and capture the LARP serial logs before changing timeouts.

## What this cannot solve in software

Multi-second control delay can still be caused by inadequate Pi or motor power,
Wi-Fi interference/range, a saturated 2.4 GHz hotspot, an ESP32 brownout,
blocked antenna, or motor noise entering a camera/ESP32 supply. The local API
benchmark proves the dashboard has no request queue of that size; it does not
replace a powered field test.
