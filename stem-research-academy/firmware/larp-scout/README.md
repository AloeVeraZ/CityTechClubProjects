# LARP scout drive firmware

This package runs the differential-drive controller on each LARP scout's ECHO
board. Flash `larp_scout_controller.ino` with `ROBOT_ID = 'A'` or `ROBOT_ID =
'B'`. It joins `3TSahur-Swarm`, reports a heartbeat to the 3TSahur hub, serves
`/drive`, `/stop`, and `/status`, and stops motors after 500 ms without a valid
command.

The LARP drive controller and its separate Inland ESP32-CAM must use the same
`A` or `B` identity. Confirm the ECHO motor IDs and direction with wheels
raised before ground operation.

## Laptop setup for the ECHO board

The drive controller is a 3DBuffalo ECHO board built around an ESP32-S3. The
following software is sufficient for both the small motor test and the full
LARP controller sketch. Git, Python, PlatformIO, and a separate ESP32-CAM
programmer are not required for this board.

1. Install the current Arduino IDE 2.x from the
   [official Arduino download page](https://www.arduino.cc/en/software/).
2. Open **Tools > Board > Boards Manager**, search for `esp32`, and install
   **esp32 by Espressif Systems**.
3. Select **Tools > Board > esp32 > ESP32S3 Dev Module**.
4. Open **Sketch > Include Library > Manage Libraries**, search for
   `Adafruit BusIO`, and install **Adafruit BusIO by Adafruit**.
5. Download **Source code (zip)** for
   [3DBuffalo EchoLib 1.3.0](https://github.com/3DBuffalo/Echo_Lib/releases/tag/V1.3.0).
   Do not unzip it. In Arduino IDE, choose **Sketch > Include Library > Add
   .ZIP Library...**, select the ZIP, and restart Arduino IDE. The sketches
   are compile-checked against 1.3.0. This release changed the drive class
   name to `TankDrive`, which the full sketch uses.

EchoLib includes all of its features through `EchoLib.h`, so Adafruit BusIO is
needed even for a motor-only sketch. `WiFi`, `WebServer`, `ESPmDNS`, and
`WiFiUdp` used by the full controller arrive with the Espressif board package;
do not install similarly named third-party libraries for them.

### Arduino Tools settings

Use the settings published for ECHO by 3DBuffalo:

| Setting | Value |
| --- | --- |
| Board | ESP32S3 Dev Module |
| USB CDC On Boot | Enabled |
| CPU Frequency | 240MHz (WiFi) |
| Core Debug Level | None |
| USB DFU On Boot | Disabled |
| Erase All Flash Before Sketch Upload | Enabled |
| Events Run On | Core 1 |
| Flash Mode | QIO 80MHz |
| Flash Size | 16MB (128Mb) |
| JTAG Adapter | Disabled |
| Arduino Runs On | Core 1 |
| USB Firmware MSC On Boot | Disabled |
| Partition Scheme | Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS) |
| PSRAM | Disabled |
| Upload Mode | USB-OTG CDC (TinyUSB) |
| Upload Speed | 115200 |
| USB Mode | USB-OTG (TinyUSB) |
| Zigbee Mode | Disabled |

Some menu items only appear after **ESP32S3 Dev Module** is selected. Leave an
option at its default if the installed Espressif package does not show that
menu item.

## Safe Motor 1 test

The test sketch is
[`motor-1-slow-test/motor-1-slow-test.ino`](motor-1-slow-test/motor-1-slow-test.ino).
It uses EchoLib's individual motor API to run only port 1 at 10% power for two
seconds, then stop for three seconds. It repeats until the board is reset or
powered off.

1. Turn the robot off before touching motor wiring. Confirm one motor is in
   the ECHO socket labeled **1**.
2. Raise the driven wheel completely off the table and keep loose wires,
   clothing, and fingers away from it. Keep the robot's power switch within
   reach.
3. Connect the ECHO to the laptop with a data-capable USB-C cable. Select the
   COM port under **Tools > Port**.
4. Open `motor-1-slow-test.ino`, click **Verify**, and wait for a successful
   compile.
5. Supply the ECHO and motors from the robot's correct 9-12 V battery/power
   system. USB is for programming and may power the controller logic, but it
   is not the motor supply.
6. Click **Upload**. If the IDE remains at `Connecting...`, hold ECHO's
   **PROG** button during the connection attempt and release it when the
   upload begins.
7. Open **Tools > Serial Monitor**, choose **115200 baud**, and watch the
   printed run/stop messages while Motor 1 turns.
8. Turn off motor power before lowering the robot or moving any connector.

Ten percent is intentionally low. A loaded DC motor may hum without turning
because of static friction. If that happens with the wheel raised, change only
`MOTOR_SPEED_PERCENT` from `10.0f` to `12.0f`, then `15.0f` if necessary. Do
not jump to a high value for the first test. Use `-10.0f` instead of `10.0f`
if the test needs the opposite direction.

## Upload the full controller after the motor test

1. Open `larp_scout_controller.ino`. Keep the adjacent `larp-scout.ino` file
   in the same folder: Arduino requires that primary tab because its name
   matches the `larp-scout` sketch folder. The controller code remains in the
   `larp_scout_controller.ino` tab.
2. Set `ROBOT_ID` to `'A'` for the first scout or `'B'` for the second. Leave
   the motor assignment at port 1 for the left motor and port 6 for the right
   motor unless the physical robot is verified to be wired differently.
3. Confirm `WIFI_SSID` and `WIFI_PASSWORD` match the Raspberry Pi hotspot.
4. Use the same board, Tools settings, COM port, and Upload process above.
5. Keep both wheels raised for the first dashboard command. Releasing a drive
   control should stop the motors, and the firmware watchdog should also stop
   them within 500 ms if commands disappear.

## Quick troubleshooting

| Problem | Fix |
| --- | --- |
| `EchoLib.h: No such file or directory` | Add the EchoLib release ZIP again, then fully restart Arduino IDE. |
| `Adafruit_I2CDevice.h: No such file or directory` | Install **Adafruit BusIO by Adafruit** from Library Manager. |
| No COM port | Use a known data USB-C cable, try another USB port, press Reset once, and recheck **Tools > Port**. Do not install a random CH340/CP210x driver unless Windows Device Manager identifies that exact USB bridge. |
| Upload stays on `Connecting...` | Confirm **USB-OTG CDC (TinyUSB)** and 115200 upload speed, then retry while holding **PROG**. |
| Serial Monitor is blank | Select 115200 baud and press ECHO's Reset button once. |
| Messages print but Motor 1 does not move | Confirm robot motor power is on, the motor is in port 1, and try 12-15% with the wheel raised. USB alone is not the motor supply. |
| A different motor moves | Power off and move the intended motor to the socket physically labeled 1; do not compensate by guessing internal GPIO pins. |
