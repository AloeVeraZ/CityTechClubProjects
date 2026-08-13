# Changes from the original project and partner integration base

## Integration base retained

The partner repository supplied the canonical project structure: `robot_server`
package, responsive keyboard/touch dashboard, NetworkManager hotspot, systemd
services, Chromium control-window support, atomic installer updates/rollback,
and a broad test suite. These are retained rather than replaced by the earlier
single-file prototype.

## 3TSahur/LARP integration

- Renamed the hub to **3TSahur** and the scouts to **LARP Scout A/B**.
- Changed default network and mDNS names to `3TSahur-Swarm`, `3tsahur.local`,
  `larp-a.local`, and `larp-b.local`.
- Added direct LARP camera panels to the existing dashboard.
- Reworked the dashboard into one tab per robot and keep only the selected
  camera stream open, preventing three simultaneous MJPEG feeds from consuming
  the Pi hotspot's control bandwidth.
- Added a LARP-tab CSI presence panel for camera-based verification.

## Mecanum motor mapping

The Pi mecanum GPIO pin pairs remain the same as the partner base. Physical
testing established the PWM pair order as front-left `5/6`, rear-left `19/16`,
front-right `20/21`, and rear-right `26/13`. The longitudinal mixer component
is inverted while the verified strafe and turn signs remain unchanged. Q/E
keyboard rotation is a pure four-motor pivot at a fixed 75% output.
`robot_server/motor.py` and its simulation test enforce this assignment.

## Documentation and verification

Added per-package READMEs, the setup and wiring guides, this change record, and
the recorded simulation results. The test suite now also checks LARP camera
firmware content and 3TSahur/LARP dashboard labels.

## Later operator and observability additions

The following additions are layered around—not inside—the partner-base motor
control path: one-active-stream robot tabs, C270 quality profiles, health
display, event timeline, snapshots, CSI calibration helper, browser gamepad,
dead-man mode, optional YOLO worker, and bounded feature polling. The latest
control tests continue to enforce route expiry/sequence checks and verify that
camera-profile, vision, snapshot, and timeline failures do not disable the
motor control API.

## Installer access

The base install workflow is retained. `installer/curl-install.sh` now offers
a small reviewable bootstrap command that downloads the versioned `install.sh`;
it does not duplicate or bypass the installer's atomic validation/rollback
workflow.
