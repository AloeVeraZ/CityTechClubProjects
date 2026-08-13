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

After the base install and reboot, install the optional COCO-pretrained YOLO11n
NCNN runtime with:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install-vision.sh | bash
```

The dashboard launcher selects that isolated runtime automatically. The model
stays unloaded until an operator enables Vision with the dashboard button or
the `C` key.
