/*
  ECHO Motor 1 Slow Test
  ======================

  Hardware: 3DBuffalo ECHO (ESP32-S3)
  Motor:    Port 1 only

  With the robot's wheels raised, this sketch runs Motor 1 at 10% power for
  two seconds, stops it for three seconds, and repeats. All motor ports are
  explicitly stopped before the first test begins.
*/

#include <EchoLib.h>

MotorControllers motors;

constexpr int MOTOR_PORT = 1;
constexpr float MOTOR_SPEED_PERCENT = 10.0f;
constexpr unsigned long RUN_TIME_MS = 2000;
constexpr unsigned long REST_TIME_MS = 3000;

void setup() {
  Serial.begin(115200);
  delay(1500);

  motors.setBrake();
  motors.stopAll();

  Serial.println("ECHO Motor 1 slow test ready.");
  Serial.println("Motor 1 will run at 10% for 2 seconds, then stop for 3 seconds.");
}

void loop() {
  Serial.println("Motor 1: slow forward");
  motors.set(MOTOR_PORT, MOTOR_SPEED_PERCENT);
  delay(RUN_TIME_MS);

  motors.set(MOTOR_PORT, 0.0f);
  Serial.println("Motor 1: stopped");
  delay(REST_TIME_MS);
}
