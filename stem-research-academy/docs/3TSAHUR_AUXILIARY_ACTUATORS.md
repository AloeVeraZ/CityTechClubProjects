# 3TSahur PCA9685 two-servo ramp setup

The Logitech camera is bolted down and has no actuator controls. The dashboard
controls only the ramp through an Adafruit PCA9685 on Raspberry Pi I2C bus 1 at
the default address `0x40`.

Channels 0 and 1 initialize at the closed position of 0 degrees when the
dashboard service starts. The ramp has exactly two persistent positions:

| Position | Channel 0 | Channel 1 |
| --- | --- | --- |
| Closed | 0 degrees | 0 degrees |
| Open | Configured open angle | Configured open angle |

## Wiring

| Raspberry Pi | PCA9685 |
| --- | --- |
| Physical pin 1, 3.3 V | `VCC` logic power |
| Physical pin 3, GPIO2/SDA1 | `SDA` |
| Physical pin 5, GPIO3/SCL1 | `SCL` |
| Physical pin 6, ground | `GND` |

The servo `V+` rail requires a supply matching the servos' rated voltage.
`VCC` powers only the PCA9685 logic and does not power the servo output rail.
Pi, PCA9685, and servo-supply grounds must share a common reference.

## Controls

Use the **Open ramp** / **Close ramp** dashboard button or press `R` while the
3TSahur workspace is active. There is no intermediate position and no camera
movement mode.

## Configuration

Persistent settings in `/etc/stem-research-academy/config.env` are:

```text
SERVO_I2C_ADDRESS=0x40
SERVO_FREQUENCY_HZ=50
SERVO_MIN_PULSE_US=1000
SERVO_MAX_PULSE_US=2000
RAMP_CHANNEL_0_OPEN_ANGLE=30
RAMP_CHANNEL_1_OPEN_ANGLE=30
```

Change the two open-angle values independently if the linkages require
different or mirrored travel. Closed always remains 0 degrees.

The installer enables I2C, installs `i2c-tools` and `python3-smbus`, and adds
the dashboard user to the `i2c` group. If the board is absent, the server
continues running and `/api/status` reports the PCA9685 error.

## Safe first test

1. Disconnect drivetrain power and remove ramp linkages.
2. Verify the servo supply voltage against each servo's data sheet.
3. Run `i2cdetect -y 1` and verify device `40` appears.
4. Start the dashboard service and confirm both channels initialize at 0.
5. Test **Open** with conservative angles before attaching the linkages.
6. Attach the linkages only after confirming closed and open do not bind.

The API routes are `GET /api/status` and `POST /api/actuators/ramp`. The ramp
request body is either `{"state":"closed"}` or `{"state":"open"}`. Status
reports `configured: true` only when the PCA9685 initializes successfully.
