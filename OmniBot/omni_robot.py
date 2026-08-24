#!/usr/bin/env python3
"""Three-motor Raspberry Pi omni robot with a pygame controller UI."""

from __future__ import annotations

import io
import os
import sys
import time

import pygame
import RPi.GPIO as GPIO

from camera_stream import CameraStream
from omni_kinematics import (
    THREE_OMNI_MOTOR_SIGNS,
    axis_deadzone,
    cardinal_lock,
    clamp,
    controller_drive_axes,
    mix_three_omni,
    next_servo_angle,
    radial_deadzone,
    shape_motor_power,
    trigger_activation,
)
from servo_hat import PositionalServo
from wifi_control import RemoteControlState, WifiControlServer

# Generic Bluetooth controller mapping (kept from the original program).
LEFT_X_AXIS = 0
LEFT_Y_AXIS = 1
# On this controller axis 4 is physical right-stick up/down. Axis 3 only gates
# sideways/diagonal input and never commands motion.
RIGHT_TURN_ORTHOGONAL_AXIS = 3
RIGHT_TURN_AXIS = 4
LEFT_TRIGGER_AXIS = 2
RIGHT_TRIGGER_AXIS = 5
BUTTON_A_INDEX = 0
BUTTON_Y_INDEX = 1
BUTTON_X_INDEX = 2

STICK_DEADZONE = 0.15
TURN_DEADZONE = 0.15
LEFT_STICK_HORIZONTAL_GATE = 0.20
RIGHT_STICK_ORTHOGONAL_GATE = 0.20
ARM_NEUTRAL_LIMIT = 0.18
ARM_NEUTRAL_SECONDS = 0.25

# BOARD pin numbering, matching the supplied wiring.
MOTOR_PINS = ((40, 38), (15, 35), (12, 16))
MOTOR_NAMES = ("Motor 0 (Front)", "Motor 1 (L-Rear)", "Motor 2 (R-Rear)")
# Motor 2 is electrically inverted by its wiring/mounting orientation.
MOTOR_SIGNS = THREE_OMNI_MOTOR_SIGNS

PWM_FREQUENCY_HZ = 1000
START_POWER = 0.75
MAXIMUM_POWER = 1.00
FULL_POWER_THRESHOLD = 0.65
BREAKAWAY_BOOST_SECONDS = 0.20
SLEW_PER_SECOND = 4.0
REVERSAL_DEADTIME_SECONDS = 0.08
ZERO_EPSILON = 0.005
# Intentionally faster than the servo's physical transit rate so full trigger
# commands maximum hardware speed rather than a software-limited sweep.
SERVO_SPEED_DEGREES_PER_SECOND = 1000.0

# The common OmniBot touchscreen is 800x480.  Keep the desktop's top panel
# exposed so its terminal, Wi-Fi, Bluetooth, and audio controls remain usable.
DISPLAY_WIDTH, DISPLAY_HEIGHT = 800, 480
try:
    TOP_PANEL_HEIGHT = max(
        0, min(120, int(os.environ.get("OMNIBOT_TOP_PANEL_HEIGHT", "40")))
    )
except ValueError:
    TOP_PANEL_HEIGHT = 40
SCREEN_WIDTH = DISPLAY_WIDTH
SCREEN_HEIGHT = max(320, DISPLAY_HEIGHT - TOP_PANEL_HEIGHT)
UI_FPS = 60
WIFI_CONTROL_PORT = int(os.environ.get("OMNIBOT_PORT", "8080"))


class Motor:
    """Bidirectional motor driven by PWM on two H-bridge input pins."""

    def __init__(self, name: str, in1: int, in2: int) -> None:
        self.name = name
        self.in1 = in1
        self.in2 = in2
        GPIO.setup(in1, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(in2, GPIO.OUT, initial=GPIO.LOW)
        self.pwm1 = GPIO.PWM(in1, PWM_FREQUENCY_HZ)
        self.pwm2 = GPIO.PWM(in2, PWM_FREQUENCY_HZ)
        self.pwm1.start(0.0)
        self.pwm2.start(0.0)
        self.current_power = 0.0
        self.blocked_until = 0.0
        self.boost_until = 0.0

    def _coast(self) -> None:
        self.pwm1.ChangeDutyCycle(0.0)
        self.pwm2.ChangeDutyCycle(0.0)
        self.current_power = 0.0

    def _write(self, power: float) -> None:
        duty = abs(power) * 100.0
        if power > 0.0:
            self.pwm2.ChangeDutyCycle(0.0)
            self.pwm1.ChangeDutyCycle(duty)
        elif power < 0.0:
            self.pwm1.ChangeDutyCycle(0.0)
            self.pwm2.ChangeDutyCycle(duty)
        else:
            self._coast()

    def command(self, target: float, now: float, dt: float) -> tuple[str, float]:
        target = clamp(target, -1.0, 1.0)
        if abs(target) < ZERO_EPSILON:
            target = 0.0

        # Neutral stops immediately. Any nonzero command starts at 50% rather
        # than wasting time ramping through a range that cannot move the robot.
        if target == 0.0:
            self._coast()
            return "OFF", 0.0

        target = shape_motor_power(
            target, START_POWER, MAXIMUM_POWER, FULL_POWER_THRESHOLD
        )

        reversing = self.current_power * target < 0.0
        if reversing:
            self._coast()
            self.blocked_until = now + REVERSAL_DEADTIME_SECONDS
            return "COAST", 0.0

        if now < self.blocked_until:
            self._coast()
            return "WAIT", 0.0

        if self.current_power == 0.0:
            # A short true-100% pulse helps overcome static friction. Full
            # stick remains at 100% after this pulse instead of ramping down.
            self.current_power = 1.0 if target > 0.0 else -1.0
            self.boost_until = now + BREAKAWAY_BOOST_SECONDS
        elif now < self.boost_until:
            self.current_power = 1.0 if target > 0.0 else -1.0
        else:
            max_change = SLEW_PER_SECOND * max(dt, 0.0)
            self.current_power += clamp(
                target - self.current_power, -max_change, max_change
            )
        self._write(self.current_power)

        if self.current_power > 0.0:
            state = "FWD"
        elif self.current_power < 0.0:
            state = "REV"
        else:
            state = "OFF"
        return state, abs(self.current_power) * 100.0

    def stop(self) -> None:
        self._coast()
        self.pwm1.stop()
        self.pwm2.stop()


def get_joystick() -> pygame.joystick.Joystick | None:
    if pygame.joystick.get_count() == 0:
        return None
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    return joystick


def main() -> None:
    # X11 honors this position directly.  On Wayland/labwc, the reduced window
    # height lets the compositor place it below the panel's reserved area.
    os.environ.setdefault("SDL_VIDEO_WINDOW_POS", f"0,{TOP_PANEL_HEIGHT}")
    pygame.init()
    pygame.joystick.init()
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME
    )
    pygame.display.set_caption("3-Motor Omni Wheel Drivetrain - Generic Controller")
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont(None, 18)
    font_medium = pygame.font.SysFont(None, 22)
    font_bold = pygame.font.SysFont(None, 26, bold=True)
    camera: CameraStream | None = None
    last_camera_frame: bytes | None = None
    camera_surface: pygame.Surface | None = None
    camera_preview: pygame.Surface | None = None

    def render(text: str, font=font_medium, color=(25, 25, 28)):
        return font.render(text, True, color)

    def draw_ui(joy_name, lx, ly, rows, enabled, armed, servo_status):
        nonlocal last_camera_frame, camera_surface, camera_preview
        screen.fill((245, 246, 248))
        center_x, center_y, radius = 140, SCREEN_HEIGHT // 2, 110
        pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), radius)
        pygame.draw.circle(
            screen, (200, 205, 210), (center_x, center_y), radius, 3
        )
        inner_radius = radius - 16
        dot_x = center_x + int(clamp(lx, -1, 1) * (inner_radius - 6))
        dot_y = center_y + int(clamp(ly, -1, 1) * (inner_radius - 6))
        pygame.draw.circle(screen, (220, 224, 229), (dot_x, dot_y), 12)

        status = "ENABLED" if enabled else "DISABLED (Press A)"
        if enabled and not armed:
            status += " - UNARMED (Center sticks briefly)"
        screen.blit(
            render(
                f"Status: {status} - Deadzone: {int(STICK_DEADZONE * 100)}%",
                font_bold,
            ),
            (14, 16),
        )
        screen.blit(
            render(f"Controller Profile: {joy_name}", font_small, (90, 96, 105)),
            (14, 42),
        )

        panel_x = 280
        panel = (panel_x, 12, SCREEN_WIDTH - 296, SCREEN_HEIGHT - 24)
        pygame.draw.rect(screen, (255, 255, 255), panel, border_radius=16)
        pygame.draw.rect(screen, (210, 215, 220), panel, 2, border_radius=16)
        y = 20
        screen.blit(render("Omni Drivetrain Telemetry", font_bold), (panel_x + 12, y))
        y += 28
        for row in rows:
            screen.blit(render(row, font_medium), (panel_x + 12, y))
            y += 28
        screen.blit(render(servo_status, font_small, (70, 76, 85)), (panel_x + 12, y + 4))
        y += 28
        screen.blit(
            render(
                f"Server: http://10.42.0.1 · port {WIFI_CONTROL_PORT}",
                font_small,
                (70, 76, 85),
            ),
            (panel_x + 12, y),
        )
        y += 22

        camera_status = camera.public_status() if camera is not None else {
            "available": False,
            "error": "Camera service is not running",
        }
        camera_label = camera_status.get("name") or "USB Camera"
        state_label = "LIVE" if camera_status.get("available") else "WAITING"
        screen.blit(
            render(f"{camera_label} · {state_label}", font_small, (70, 76, 85)),
            (panel_x + 12, y),
        )
        video_top = y + 20
        video_rect = pygame.Rect(
            panel_x + 12,
            video_top,
            panel[2] - 24,
            max(80, panel[1] + panel[3] - video_top - 12),
        )
        pygame.draw.rect(screen, (20, 22, 26), video_rect, border_radius=8)

        frame = camera.latest_jpeg() if camera is not None else None
        if frame is not None and frame is not last_camera_frame:
            try:
                camera_surface = pygame.image.load(io.BytesIO(frame)).convert()
                source_width, source_height = camera_surface.get_size()
                scale = min(
                    video_rect.width / source_width,
                    video_rect.height / source_height,
                )
                size = (
                    max(1, round(source_width * scale)),
                    max(1, round(source_height * scale)),
                )
                camera_preview = pygame.transform.smoothscale(camera_surface, size)
                last_camera_frame = frame
            except pygame.error:
                camera_surface = None
                camera_preview = None
                last_camera_frame = frame
        if camera_preview is not None and camera_status.get("available"):
            target = camera_preview.get_rect(center=video_rect.center)
            screen.blit(camera_preview, target)
        else:
            message = str(camera_status.get("error") or "Waiting for camera")
            if len(message) > 56:
                message = message[:53] + "..."
            placeholder = render(message, font_small, (202, 207, 214))
            screen.blit(placeholder, placeholder.get_rect(center=video_rect.center))
        pygame.display.flip()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    motors = [
        Motor(name, pins[0], pins[1])
        for name, pins in zip(MOTOR_NAMES, MOTOR_PINS)
    ]
    servo: PositionalServo | None = None
    servo_error = ""
    try:
        servo = PositionalServo()
    except Exception as error:
        servo_error = f"Servo 0 unavailable: {error}"
    joystick = get_joystick()
    remote_control = RemoteControlState()
    camera = CameraStream.from_environment().start()
    wifi_server: WifiControlServer | None = None
    try:
        wifi_server = WifiControlServer(
            remote_control, port=WIFI_CONTROL_PORT, camera=camera
        ).start()
        print(f"OmniBot Wi-Fi controller listening on port {wifi_server.port}")
    except OSError as error:
        # The robot's local controller and display must remain usable even if
        # the network port is temporarily unavailable.
        print(f"OmniBot Wi-Fi controller unavailable: {error}", file=sys.stderr)

    enabled = False
    armed = False
    control_source = "none"
    remote_generation = remote_control.consume().generation
    neutral_since: float | None = None
    previous_a = False
    previous_y = False
    running = True
    last_time = time.monotonic()
    left_trigger_rest = 0.0
    right_trigger_rest = 0.0

    def all_stop() -> None:
        stop_time = time.monotonic()
        for motor in motors:
            motor.command(0.0, stop_time, 1.0)

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    joystick = get_joystick()
                    if joystick is None and control_source == "local":
                        enabled = armed = False
                        control_source = "none"
                        all_stop()

            now = time.monotonic()
            dt = min(now - last_time, 0.1)
            last_time = now
            remote_input = remote_control.consume(now)
            if remote_input.generation != remote_generation:
                remote_generation = remote_input.generation
                if remote_input.enabled:
                    control_source = "wifi"
                    enabled = True
                    armed = False
                    neutral_since = None
                    all_stop()
                elif control_source == "wifi":
                    control_source = "none"
                    enabled = armed = False
                    neutral_since = None
                    all_stop()

            if control_source == "wifi":
                joy_name = "Laptop browser over OmniBot Wi-Fi"
            elif joystick:
                joy_name = joystick.get_name()
            else:
                joy_name = "No local controller - Wi-Fi ready"

            def axis(index: int) -> float:
                if joystick is None or index >= joystick.get_numaxes():
                    return 0.0
                return joystick.get_axis(index)

            def button(index: int) -> bool:
                return bool(
                    joystick is not None
                    and index < joystick.get_numbuttons()
                    and joystick.get_button(index)
                )

            if control_source == "wifi":
                # Remote values are already expressed in the robot's logical
                # directions. Convert only the display/controller convention;
                # the original deadzones, cardinal lock, and omni mixer below
                # are still applied without modification.
                lx_raw = -remote_input.strafe
                ly_raw = -remote_input.forward
                right_orthogonal_raw = 0.0
                right_turn_raw = remote_input.turn
                left_trigger_raw = remote_input.left_trigger
                right_trigger_raw = remote_input.right_trigger
            else:
                lx_raw = axis(LEFT_X_AXIS)
                ly_raw = axis(LEFT_Y_AXIS)
                right_orthogonal_raw = axis(RIGHT_TURN_ORTHOGONAL_AXIS)
                right_turn_raw = axis(RIGHT_TURN_AXIS)
                left_trigger_raw = axis(LEFT_TRIGGER_AXIS)
                right_trigger_raw = axis(RIGHT_TRIGGER_AXIS)
            a_pressed = button(BUTTON_A_INDEX)
            y_pressed = button(BUTTON_Y_INDEX)
            x_pressed = button(BUTTON_X_INDEX) or (
                control_source == "wifi" and remote_input.center_servo
            )

            # Rising edges prevent a held A button from resetting arming each frame.
            if y_pressed and not previous_y:
                remote_control.stop()
                remote_generation = remote_control.consume().generation
                enabled = armed = False
                control_source = "none"
                neutral_since = None
                all_stop()
            elif a_pressed and not previous_a:
                remote_control.stop()
                remote_generation = remote_control.consume().generation
                control_source = "local"
                enabled = True
                armed = False
                neutral_since = None
                # A local controller can take over while Wi-Fi input is still
                # present in this frame. Calibrate from the physical trigger
                # axes, not from the just-replaced remote values.
                left_trigger_rest = axis(LEFT_TRIGGER_AXIS)
                right_trigger_rest = axis(RIGHT_TRIGGER_AXIS)
                all_stop()
            previous_a, previous_y = a_pressed, y_pressed

            strafe_raw, forward_raw, turn_raw = controller_drive_axes(
                lx_raw,
                ly_raw,
                right_turn_raw,
                right_orthogonal_raw,
                RIGHT_STICK_ORTHOGONAL_GATE,
            )
            strafe, forward = radial_deadzone(
                strafe_raw, forward_raw, STICK_DEADZONE
            )
            strafe, forward = cardinal_lock(
                strafe, forward, LEFT_STICK_HORIZONTAL_GATE
            )
            turn = axis_deadzone(turn_raw, TURN_DEADZONE)
            neutral = max((strafe * strafe + forward * forward) ** 0.5, abs(turn))

            if control_source == "wifi":
                left_trigger = left_trigger_raw
                right_trigger = right_trigger_raw
            else:
                left_trigger = trigger_activation(
                    left_trigger_raw, left_trigger_rest
                )
                right_trigger = trigger_activation(
                    right_trigger_raw, right_trigger_rest
                )

            if servo is not None:
                if enabled and armed:
                    if x_pressed:
                        servo.center()
                    else:
                        servo.set_angle(
                            next_servo_angle(
                                servo.angle,
                                left_trigger,
                                right_trigger,
                                dt,
                                SERVO_SPEED_DEGREES_PER_SECOND,
                            )
                        )
                servo_status = (
                    f"Servo 0: {servo.angle:+6.1f} deg  "
                    f"LT {left_trigger*100:3.0f}%  RT {right_trigger*100:3.0f}%  "
                    "X = center"
                )
            else:
                servo_status = servo_error

            if enabled and not armed:
                if neutral <= ARM_NEUTRAL_LIMIT:
                    if neutral_since is None:
                        neutral_since = now
                    elif now - neutral_since >= ARM_NEUTRAL_SECONDS:
                        armed = True
                else:
                    neutral_since = None

            telemetry = []
            input_connected = (
                remote_input.enabled
                if control_source == "wifi"
                else joystick is not None
            )
            if not enabled or not armed or not input_connected:
                all_stop()
                if not input_connected and enabled:
                    reason = "STOPPED (Controller disconnected)"
                elif not enabled:
                    reason = "STOPPED (System disabled)"
                else:
                    reason = "SAFE (Return sticks to center)"
                telemetry = [f"{name}: {reason}" for name in MOTOR_NAMES]
            else:
                powers = mix_three_omni(strafe, forward, turn)
                for motor, sign, target in zip(motors, MOTOR_SIGNS, powers):
                    signed_target = target * sign
                    state, duty = motor.command(signed_target, now, dt)
                    target_duty = abs(
                        shape_motor_power(
                            signed_target,
                            START_POWER,
                            MAXIMUM_POWER,
                            FULL_POWER_THRESHOLD,
                        )
                    ) * 100.0
                    telemetry.append(
                        f"{motor.name}: {state:5} Target {target_duty:5.1f}% "
                        f"Current {duty:5.1f}%"
                    )

            draw_ui(
                joy_name, lx_raw, ly_raw, telemetry, enabled, armed, servo_status
            )
            remote_control.report_runtime(
                enabled=enabled,
                armed=armed,
                source=control_source,
                telemetry=telemetry,
                servo=servo_status,
            )
            clock.tick(UI_FPS)
    finally:
        for motor in motors:
            motor.stop()
        if servo is not None:
            servo.close()
        if wifi_server is not None:
            wifi_server.close()
        if camera is not None:
            camera.close()
        GPIO.cleanup()
        pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
