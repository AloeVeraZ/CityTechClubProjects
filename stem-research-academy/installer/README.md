# 3TSahur installer

`install.sh` provisions Raspberry Pi OS for the large 3TSahur robot. It installs
the required system packages, creates the `3TSahur-Swarm` NetworkManager
hotspot, deploys the dashboard systemd service, configures mDNS and the local
Chromium dashboard window, and validates a replacement installation before
atomically swapping it into place.

Run it as the normal Pi user, not as root, from a trusted checkout:

```bash
bash installer/install.sh
```

The installer intentionally reboots when complete. See
[../docs/SETUP.md](../docs/SETUP.md) for preparation, installation, and raised-
wheel safety checks.
