# ECHO Scout firmware

`ECHO_Robot_Controller.ino` is the shared sketch for both identical differential-drive mini robots. Set `ROBOT_ID` to `A` before flashing the first ECHO board and to `B` before flashing the second. No other source fork is needed.

## What the sketch does

1. Initializes ECHO motor channels 1 and 6, enables brake mode, and explicitly commands zero speed.
2. Joins the Raspberry Pi's `EchoSwarm` network as a Wi-Fi station using password `roboswarm1`.
3. Requests an address from the Pi hotspot and advertises `echo-scout-a.local` or `echo-scout-b.local` with mDNS.
4. Hosts a small standalone touch-control page at the robot's `.local` address.
5. Exposes `/drive`, `/stop`, `/status`, and `/motion` endpoints for the central Pi dashboard.
6. Applies a 500 ms command watchdog, stopping both motors if the browser, Pi, or Wi-Fi link disappears.
7. Samples Wi-Fi Channel State Information and reports a coarse nearby-disturbance level in `/status`.
8. Sends compact CSI summaries to UDP port 5005 on the Pi for future research processing.
9. Broadcasts a heartbeat to UDP port 5006 once per second, allowing the Pi to confirm connection and learn the scout's current DHCP address without relying on `.local` resolution.

The CSI result only means that Wi-Fi multipath changed. It cannot identify a person, determine direction or distance, count occupants, or replace a camera. Its threshold must be tuned in the actual room.

## Required Arduino setup

- Board: **ESP32S3 Dev Module**, unless 3DBuffalo supplies a more specific ECHO profile.
- ESP32 board support from Espressif Systems.
- EchoLib from 3DBuffalo.
- EchoLib's documented dependencies, including Adafruit BusIO.

The sketch uses the documented `MotorControllers` and `TankDriveTrain` APIs. Motor 1 is treated as the left side and Motor 6 as the right side, matching 3DBuffalo's Zippy example.

## First motor test

The provided motor assignment has not been physically validated. Lift the wheels clear of the floor, disconnect any payload, keep access to motor power, and leave the default 35% speed limit in place. Flash Scout A first and open `http://echo-scout-a.local` while connected to `EchoSwarm`.

If forward makes one side run backward, change only the appropriate constant:

```cpp
constexpr bool REVERSE_LEFT_MOTOR = false;
constexpr bool REVERSE_RIGHT_MOTOR = false;
```

Do not compensate for reversed wiring by swapping unrelated motor IDs in several functions.

## Camera integration

This ECHO sketch does not invent camera pin mappings. If each scout has a separate ESP32-CAM streamer, configure those boards as `echo-scout-a-cam.local` and `echo-scout-b-cam.local` with `/stream` endpoints. The central HUD already uses those addresses. If the camera is electrically attached to the ECHO ESP32-S3 itself, its exact sensor model and pin map are required before camera firmware can safely be added.
