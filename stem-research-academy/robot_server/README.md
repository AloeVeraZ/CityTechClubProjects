# 3TSahur robot server

`robot_server` is the Python package that runs on the Raspberry Pi 4. It serves
the browser dashboard, captures the Logitech USB camera, mixes mecanum commands
into four PWM motor outputs, controls the two-servo ramp, and reports basic
system health.

Run it locally with `python -m robot_server.app` after installing
`requirements.txt`. Without `RPi.GPIO`, motor commands run in simulation mode;
without `pigpiod`, ramp commands remain disabled. The API and dashboard remain
available so the software can be tested away from the robot.

Production deployment is performed by the repository installer. Hardware pin
mapping and safety checks are documented in
[../docs/WIRING.md](../docs/WIRING.md).
