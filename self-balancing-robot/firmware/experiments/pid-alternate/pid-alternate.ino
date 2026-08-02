#include <Wire.h>

// ===================== 1. PINS & CONFIG =====================
const int MPU_ADDR = 0x68;
const int ENA = 5, IN1 = 2, IN2 = 4; // Motor A
const int ENB = 9, IN3 = 7, IN4 = 8; // Motor B

// ===================== 2. TUNING (THE FIXES) =====================
// PID CONSTANTS
float Kp = 18.0;   // Power of the reaction
float Ki = 60.0;  // Fixes leaning/drifting
float Kd = 0.6;    // Dampens shaking (The "Brakes")

// ANGLE OFFSETS
// Adjust this until the wheels STOP spinning when you hold it upright.
// If it falls forward: decrease this. If it falls backward: increase this.
float targetAngle = -2; 

// SENSOR FILTERING
// 0.99 means 99% Gyro (smooth) and 1% Accel (stable). 
const float alpha = 0.99; 

// ===================== STATE VARIABLES =====================
float pitch = 0;
float gyroYOffset = 0;
float integratedError = 0;
float lastError = 0;
unsigned long timer;
const int LOOP_TIME_MS = 5; // 200Hz loop
float dt = 0.005;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000); // High speed I2C

  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  setupMPU();
  calibrateGyro();
  
  // Flash LED or Print to show ready
  Serial.println("Robot Ready. Keep it level!");
  delay(1000);
  
  timer = micros();
}

void loop() {
  // --- FIXED LOOP TIMER ---
  // This ensures the PID math stays consistent
  while (micros() - timer < 5000); 
  timer = micros();

  // 1. GET SENSOR DATA
  readPitch();

  // 2. SAFETY CUTOFF
  // If the robot falls over 45 degrees, kill the motors
  if (abs(pitch) > 45) {
    stopMotors();
    integratedError = 0; 
    return;
  }

  // 3. PID CALCULATION
  float error = pitch - targetAngle;
  
  // Integral: Accumulates error over time to fix drift
  integratedError += error * dt;
  integratedError = constrain(integratedError, -200, 200); 
  
  // Derivative: Measures how fast we are falling to apply "brakes"
  float derivative = (error - lastError) / dt;
  lastError = error;

  float output = (Kp * error) + (Ki * integratedError) + (Kd * derivative);

  // 4. MOTOR DRIVE
  controlMotors(output);
  
  // Debug: Use Serial Plotter to see if Pitch matches Target
  // Serial.print(pitch); Serial.print(","); Serial.println(targetAngle);
}

// ===================== MOTOR CONTROL =====================

void controlMotors(float output) {
  int speed = (int)output;
  
  // Deadzone Compensation: Gives the motors a "kick" to start moving
  // Increase this if the robot hums but doesn't move at small angles.
  int minPower = 35; 
  if (speed > 0) speed += minPower;
  if (speed < 0) speed -= minPower;

  speed = constrain(speed, -255, 255);

  if (speed > 0) { // Tipping Forward -> Move Forward
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  } else {         // Tipping Backward -> Move Backward
    digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
  }

  analogWrite(ENA, abs(speed));
  analogWrite(ENB, abs(speed));
}

void stopMotors() {
  analogWrite(ENA, 0); analogWrite(ENB, 0);
}

// ===================== SENSOR FUSION =====================

void setupMPU() {
  writeReg(0x6B, 0x00); // Wake up
  writeReg(0x1A, 0x03); // Enable Digital Low Pass Filter (DLPF) 
  writeReg(0x1B, 0x00); // Gyro +/- 250 deg/s
}

void readPitch() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); // Skip temp
  Wire.read(); Wire.read(); // Skip Gyro X
  int16_t gy = (Wire.read() << 8) | Wire.read();

  // Accelerometer math
  float accelAngle = atan2(-ax, sqrt((long)ay * ay + (long)az * az)) * 57.295;
  // Gyro math
  float gyroRate = (gy - gyroYOffset) / 131.0;

  // COMPLEMENTARY FILTER FIX:
  // Combines gyro (smooth/fast) and accel (stable/slow)
  pitch = alpha * (pitch + gyroRate * dt) + (1.0 - alpha) * accelAngle;
}

void calibrateGyro() {
  long sum = 0;
  for (int i = 0; i < 500; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x45); 
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 2, true);
    sum += (int16_t)(Wire.read() << 8 | Wire.read());
    delay(2);
  }
  gyroYOffset = sum / 500.0;
}

void writeReg(byte reg, byte val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}
