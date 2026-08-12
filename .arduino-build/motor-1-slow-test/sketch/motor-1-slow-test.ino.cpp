#line 1 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
/*
  ECHO Motor 1 Slow Test -- no EchoLib required
  =================================================

  Pin map extracted from the official 3DBuffalo EchoLib motor source:
    Motor 1: GPIO 47 / 48   MCPWM unit 0, timer 0
    Motor 2: GPIO 38 / 21   MCPWM unit 0, timer 1
    Motor 3: GPIO  1 /  2   MCPWM unit 0, timer 2
    Motor 4: GPIO  4 /  5   MCPWM unit 1, timer 0
    Motor 5: GPIO  7 /  6   MCPWM unit 1, timer 1
    Motor 6: GPIO 16 / 15   MCPWM unit 1, timer 2

  This sketch initializes only Motor 1 and waits safely at zero power. Send
  G over the Serial Monitor to run at 10% for two seconds exactly once. Send
  S at any time to stop.
*/

#include <Arduino.h>
#include "driver/mcpwm.h"

constexpr int MOTOR_1_PIN_A = 47;
constexpr int MOTOR_1_PIN_B = 48;
constexpr float MOTOR_SPEED_PERCENT = 10.0f;
constexpr unsigned long RUN_TIME_MS = 2000;

#line 26 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
void stopMotor1();
#line 32 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
void setMotor1(float percent);
#line 50 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
void setup();
#line 71 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
void loop();
#line 26 "C:\\CityTechClubProjects\\stem-research-academy\\firmware\\larp-scout\\motor-1-slow-test\\motor-1-slow-test.ino"
void stopMotor1() {
  // EchoLib's brake/zero behavior: both DRV8874 control inputs held low.
  mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A);
  mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B);
}

void setMotor1(float percent) {
  percent = constrain(percent, -100.0f, 100.0f);

  if (percent == 0.0f) {
    stopMotor1();
  } else if (percent > 0.0f) {
    mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, percent);
    mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0,
                        MCPWM_OPR_A, MCPWM_DUTY_MODE_0);
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B);
  } else {
    mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, -percent);
    mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0,
                        MCPWM_OPR_B, MCPWM_DUTY_MODE_0);
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, MOTOR_1_PIN_A);
  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, MOTOR_1_PIN_B);

  mcpwm_config_t config = {};
  config.frequency = 1000;
  config.cmpr_a = 0;
  config.cmpr_b = 0;
  config.duty_mode = MCPWM_DUTY_MODE_0;
  config.counter_mode = MCPWM_UP_COUNTER;
  mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &config);
  mcpwm_start(MCPWM_UNIT_0, MCPWM_TIMER_0);

  stopMotor1();
  Serial.println("Direct ECHO Motor 1 test ready (no EchoLib).");
  Serial.println("Send G to run once. Send S to stop.");
}

void loop() {
  if (!Serial.available()) return;

  const char command = Serial.read();
  if (command == 'g' || command == 'G') {
    Serial.println("Motor 1: 10% forward for 2 seconds");
    setMotor1(MOTOR_SPEED_PERCENT);
    delay(RUN_TIME_MS);
    stopMotor1();
    Serial.println("Motor 1: stopped. Send G to test again.");
  } else if (command == 's' || command == 'S') {
    stopMotor1();
    Serial.println("Motor 1: emergency stop");
  }
}

