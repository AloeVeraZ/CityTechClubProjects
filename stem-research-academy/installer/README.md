# 3TSahur installer

`install.sh` provisions Raspberry Pi OS for 3TSahur. It installs system
packages, creates the `3TSahur-Swarm` NetworkManager hotspot, deploys the
dashboard systemd service, configures mDNS and a Chromium control window, and
validates a replacement installation before atomically swapping it into place.

Run it as the normal Pi user—not as root—from a trusted checkout:

```bash
bash installer/install.sh
```

It intentionally reboots when complete. See [../docs/SETUP.md](../docs/SETUP.md)
for preparation, flashing order, and safety checks.

After the base install and reboot, install compact 80-class offline object
detection with:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install-vision.sh | bash
```

The installer downloads checksum-verified YOLOv4-tiny COCO weights and validates
a real person detection through the same system OpenCV runtime used by the
camera. No second Python environment or internet connection is required after
installation. Press `C` to enable or disable boxes.
