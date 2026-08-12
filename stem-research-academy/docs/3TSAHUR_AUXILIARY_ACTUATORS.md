# 3TSahur direct-GPIO ramp servos

The Logitech camera is bolted down and has no actuator controls. Two hobby
servos operate the ramp directly from Raspberry Pi GPIO signals.

## Pinout

| Servo | Signal | Power | Ground |
| --- | --- | --- | --- |
| Ramp Servo 1 | BCM GPIO12, physical pin 32 | 5 V, physical pin 2 | Physical pin 6 |
| Ramp Servo 2 | BCM GPIO18, physical pin 12 | 5 V, physical pin 4 | Physical pin 14 |

Typical servo colors are red for power, brown/black for ground, and
orange/white/yellow for signal. Verify the colors for the exact servo before
applying power. Do not put 5 V onto GPIO12 or GPIO18; Pi GPIO signals are 3.3 V.

## Positions and controls

| Position | Servo 1 | Servo 2 |
| --- | ---: | ---: |
| Closed/startup | 0 degrees | 0 degrees |
| Open | 30 degrees | 30 degrees |

Use **Open ramp** / **Close ramp** in the dashboard or press `R` while the
3TSahur workspace is active. There is no intermediate position and no camera
movement mode.

## Configuration

Persistent settings in `/etc/stem-research-academy/config.env` are:

```text
RAMP_SERVO_0_GPIO_BCM=12
RAMP_SERVO_1_GPIO_BCM=18
RAMP_SERVO_FREQUENCY_HZ=50
RAMP_SERVO_MIN_PULSE_US=1000
RAMP_SERVO_MAX_PULSE_US=2000
```

The installer provides `python3-rpi.gpio`. The application starts both PWM
signals at the 0-degree duty cycle and keeps the selected position active.

## Power warning

The two 5 V header pins share the Pi's main 5 V rail; they are not two separate
power supplies. Direct header power is only safe when the Pi power supply has
enough remaining capacity for both servos, including startup and stall current.
Servo current spikes can cause undervoltage, resets, or permanent damage.

For the first test, disconnect drivetrain power and remove the ramp linkages.
If the Pi reports undervoltage, resets, or the servos chatter, disconnect the
servo red wires and use a separate regulated 5 V supply. With an external
supply, connect its ground to Pi ground so the GPIO signals have a common
reference.

The API routes are `GET /api/status` and `POST /api/actuators/ramp`. The request
body is either `{"state":"closed"}` or `{"state":"open"}`.
