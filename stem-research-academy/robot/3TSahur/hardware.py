"""Pin and name definitions for the 3TSahur mecanum robot.

This is 3TSahur's own wiring, not the MotionModule reference wiring. It is the
same BCM GPIO map the original 3TSahur server drove (docs/WIRING.md), so the
robot runs on MotionModule without moving a single wire:

    channel  name          driver / output   forward GPIO   reverse GPIO
    -------  ------------  ---------------   ------------   ------------
       1     front_left    Driver 1 · A      GPIO5          GPIO6
       2     rear_left     Driver 1 · B      GPIO19         GPIO16
       3     front_right   Driver 2 · A      GPIO20         GPIO21
       4     rear_right    Driver 2 · B      GPIO26         GPIO13

The rear pairs were already polarity-swapped in the original pin map, so no
motor is `inverted` here. mixer.py carries the robot's tested drive math.

The two ramp servos are plain GPIO signals (GPIO12 and GPIO18) timed by the
pigpio daemon, not a PCA9685 board, so MotionModule's servo board support is
switched off below. ramp.py drives them.

MotionModule reads this file as data. No imports, `if` statements, or function
calls.
"""

HARDWARE = {
    "module": {
        "pwm_hz": 1000,      # The original 3TSahur motor PWM frequency.
        "deadtime_ms": 15,   # Coast time before any motor reverses.
        "watchdog_ms": 300,  # All motors stop if commands stop arriving.
    },

    "motors": {
        1: {"name": "front_left", "forward_gpio": 5, "reverse_gpio": 6, "inverted": False},
        2: {"name": "rear_left", "forward_gpio": 19, "reverse_gpio": 16, "inverted": False},
        3: {"name": "front_right", "forward_gpio": 20, "reverse_gpio": 21, "inverted": False},
        4: {"name": "rear_right", "forward_gpio": 26, "reverse_gpio": 13, "inverted": False},
    },

    # 3TSahur has no PCA9685. MotionModule still needs these values to be
    # valid, but with "enabled" False it never opens the I2C bus.
    "servos": {
        "enabled": False,
        "i2c_bus": 1,
        "frequency_hz": 50,
        "addresses": [0x40],
        "output_enable_gpio": None,
        "minimum_pulse_us": 1000,
        "maximum_pulse_us": 2000,
    },
}
