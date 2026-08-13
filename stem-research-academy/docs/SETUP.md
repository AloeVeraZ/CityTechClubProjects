# 3TSahur setup guide

## 1. Prepare the hardware safely

Keep all four wheels raised. Connect a physical motor-power switch and a
correctly rated fuse. Connect a shared ground between the Raspberry Pi, both
motor drivers, and the motor supply. Never power the drive motors from the
Raspberry Pi 5 V rail.

Wire the Pi exactly as [WIRING.md](WIRING.md) specifies, connect the ramp servos
to their regulated 5 V supply, and attach the Logitech USB camera.

## 2. Install on the Raspberry Pi

Use a current Raspberry Pi OS image with internet access. Clone the repository
and run the installer as the normal Pi user:

```bash
git clone https://github.com/AloeVeraZ/CityTechClubProjects.git
cd CityTechClubProjects/stem-research-academy
bash installer/install.sh
```

The installer configures the existing `3TSahur-Swarm` 2.4 GHz hotspot, sets the
hostname to `3tsahur`, starts the dashboard at boot, and reboots. Connect an
operator device to the hotspot and open `http://10.42.0.1`.

## 3. Validate without driving on the floor

1. Confirm that the dashboard loads and the Logitech camera stream appears.
2. Confirm that GPIO, camera, and servo status appear in the system panel.
3. Keep the wheels raised and select a low speed.
4. Test forward, backward, left strafe, right strafe, and both rotations.
5. Release each key and verify that all four motors stop.
6. Test the ramp with its linkage disconnected or clear of obstructions.
7. Verify that `Space`, `Esc`, focus loss, and the watchdog stop the drivetrain.
8. Perform a floor test only after every direction and stop path is correct.

## Nginx validation during an update

The installer resolves Nginx at `/usr/sbin/nginx` when it is not in the normal
user's `PATH`, validates the generated dashboard proxy before changing active
sites, and avoids declarations that conflict with the Raspberry Pi OS default
site. If validation fails, the installer prints the diagnostic and removes the
new site link. Repair the reported site or reinstall the package with
`sudo apt-get install --reinstall nginx-light`, then rerun the installer.
