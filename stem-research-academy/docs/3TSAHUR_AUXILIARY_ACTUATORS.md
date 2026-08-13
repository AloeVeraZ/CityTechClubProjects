# 3TSahur direct-GPIO ramp servos

The Logitech camera is bolted down and has no actuator controls. Two hobby
servos operate the ramp directly from Raspberry Pi GPIO signals.

## Pinout

| Servo | Signal | Power | Ground |
| --- | --- | --- | --- |
| Ramp Servo 1 | BCM GPIO12, physical pin 32 | Buck +5 V | Buck ground |
| Ramp Servo 2 | BCM GPIO18, physical pin 12 | Buck +5 V | Buck ground |

Also connect the buck-converter ground to a Pi ground such as physical pin 6 or
14. This common reference is required even though servo power comes from the
battery and buck converter.

Typical servo colors are red for power, brown/black for ground, and
orange/white/yellow for signal. Verify the colors for the exact servo before
applying power. Do not put 5 V onto GPIO12 or GPIO18; Pi GPIO signals are 3.3 V.

## Positions and controls

| Position | Servo 1 | Servo 2 |
| --- | ---: | ---: |
| Closed/startup | 0 degrees | 0 degrees |
| Open | 100 degrees | 100 degrees |

These are logical ramp angles. Servo 2 on physical pin 12 is mirrored in code:
logical 0 degrees uses its 100-degree electrical position to pull in, and
logical 100 degrees uses its 0-degree electrical position to push out. Servo 1
on physical pin 32 keeps the normal direction.

Use **Open ramp** / **Close ramp** in the dashboard or press `R` while the
3TSahur workspace is active. There is no intermediate position and no camera
movement mode.

## Configuration

Persistent settings in `/etc/stem-research-academy/config.env` are:

```text
RAMP_SERVO_0_GPIO_BCM=12
RAMP_SERVO_1_GPIO_BCM=18
RAMP_SERVO_0_REVERSED=0
RAMP_SERVO_1_REVERSED=1
RAMP_SERVO_MIN_PULSE_US=1000
RAMP_SERVO_MAX_PULSE_US=2000
```

The installer uses Raspberry Pi OS packages when both are available. If the
`pigpio` daemon has no APT installation candidate, it builds official pigpio
v79 from source instead. It starts `pigpiod` and requires that daemon before
starting the dashboard. The normal servo uses 1000 microseconds when closed and
1556 microseconds when open. The reversed physical-pin-12 servo uses 1556
microseconds when closed and 1000 microseconds when open. `pigpio` continuously
holds those pulses and times their edges independently of the dashboard's Linux
process, avoiding software-PWM scheduling jitter.

## Buck-converter checks

Measure the buck output before connecting the servos and set it to 5.0 V. Its
continuous and peak current ratings must cover both servos together. Place a
bulk capacitor near the servo power split if the converter manufacturer or
servo documentation recommends one.

For the first test, disconnect drivetrain power and remove the ramp linkages.
If jitter remains, confirm the buck-to-Pi common ground first, then check the
buck voltage while both servos move. A sagging/noisy supply or a mechanically
stalled servo cannot be corrected in software.

The API routes are `GET /api/status` and `POST /api/actuators/ramp`. The request
body is either `{"state":"closed"}` or `{"state":"open"}`.
