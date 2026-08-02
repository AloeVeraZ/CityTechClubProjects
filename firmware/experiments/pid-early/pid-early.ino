#include <Wire.h>

// MPU6050 const
const int MPU_ADDR = 0x68;

int16_t accX, accY, accZ;
int16_t gyroX, gyroY, gyroZ;

float roll = 0.0f;
float pitch = 0.0f;
float yaw = 0.0f;

unsigned long lastMicros = 0;

// driver pins 
// Motor B
int ENB = 9;
int IN4 = 8;
int IN3 = 7;

// Motor A
int ENA = 5;
int IN2 = 4;
int IN1 = 2;

// PID CHANGE VARIABLES YAYY
float Kp = 90.0;
float Ki = 0.8;
float Kd = 1.2;

// Balance point offset (if center of gravity bad)
float targetAngle = 0.0;

//  PID VMKMENT ARIABLES idk significance but stackoverflow knows i think....
float error = 0;
float previousError = 0;
float integral = 0;
float derivative = 0;
float pidOutput = 0;

// change for motor control 
int maxMotorSpeed = 180;     // 0 to 255 on both motors EN pin
float integralLimit = 100.0; // idk what this does google said to keep
float deadband = 1.0;        // degree tolerance (+-)
float fallAngle = 35.0;      // stop motors robot falls too far (+-)

// Imu workie 

void mpuWrite(byte reg, byte data) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

void readMPU() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  accX = (Wire.read() << 8) | Wire.read();
  accY = (Wire.read() << 8) | Wire.read();
  accZ = (Wire.read() << 8) | Wire.read();

  Wire.read(); Wire.read(); // skip temperature

  gyroX = (Wire.read() << 8) | Wire.read();
  gyroY = (Wire.read() << 8) | Wire.read();
  gyroZ = (Wire.read() << 8) | Wire.read();
}

// make motor work yes 
void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void setMotorSpeed(int speedValue) {
  speedValue = constrain(speedValue, -maxMotorSpeed, maxMotorSpeed);

  if (speedValue > 0) {
    // fwd
    digitalWrite(IN4, HIGH);
    digitalWrite(IN3, LOW);

    digitalWrite(IN2, HIGH);
    digitalWrite(IN1, LOW);

    analogWrite(ENB, speedValue);
    analogWrite(ENA, speedValue);
  }
  else if (speedValue < 0) {
    int pwm = -speedValue;

    // reverse
    digitalWrite(IN4, LOW);
    digitalWrite(IN3, HIGH);

    digitalWrite(IN2, LOW);
    digitalWrite(IN1, HIGH);

    analogWrite(ENB, pwm);
    analogWrite(ENA, pwm);
  }
  else {
    stopMotors();
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Motor setup
  pinMode(ENB, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(IN3, OUTPUT);

  pinMode(ENA, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN1, OUTPUT);

  stopMotors();

  // MPU6050 setup
  mpuWrite(0x6B, 0x00); // start
  mpuWrite(0x1B, 0x00); // gyro ±250 deg/s
  mpuWrite(0x1C, 0x00); // accel ±2g

  delay(1000);

  //  timer start
  lastMicros = micros();

  Serial.println("pitch pidOutput motorSpeed"); //u can keep robot plugged into laptop if the batt is plugged into Vin and arduino gnd.
}                                               //Ake sure IMU is 5v on arduino gnd not battery gnd

void loop() {
  readMPU();

  unsigned long now = micros();
  float dt = (now - lastMicros) / 1000000.0f;
  lastMicros = now;

  // fix against bad dt
  if (dt <= 0 || dt > 0.1) dt = 0.01;

  // accelerometer to g
  float ax = accX / 16384.0f;
  float ay = accY / 16384.0f;
  float az = accZ / 16384.0f;

  // gyro to deg/s
  float gx = gyroX / 131.0f;
  float gy = gyroY / 131.0f;
  float gz = gyroZ / 131.0f;

  // angles
  float accelRoll  = atan2(ay, az) * 180.0f / PI;
  float accelPitch = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0f / PI;

  // gyro texh 
  float gyroRoll  = roll + gx * dt;
  float gyroPitch = pitch + gy * dt;
  yaw += gz * dt;

  // idk what this does gemini does tho
  const float alpha = 0.98f;
  roll  = alpha * gyroRoll  + (1.0f - alpha) * accelRoll;
  pitch = alpha * gyroPitch + (1.0f - alpha) * accelPitch;

  // cutoff if bad agle 
  if (abs(pitch) > fallAngle) {
    stopMotors();
    integral = 0;
    previousError = 0;

    Serial.print(pitch);
    Serial.print(' ');
    Serial.print(0);
    Serial.print(' ');
    Serial.println(0);

    delay(10);
    return;
  }

  // MORE PID MOMENTT
  error = targetAngle - pitch;

  if (abs(error) < deadband) {
    error = 0;
  }

  integral += error * dt;
  integral = constrain(integral, -integralLimit, integralLimit);

  derivative = (error - previousError) / dt;

  pidOutput = (Kp * error) + (Ki * integral) + (Kd * derivative);
  previousError = error;

  int motorSpeed = (int)pidOutput;
  motorSpeed = constrain(motorSpeed, -maxMotorSpeed, maxMotorSpeed);

  setMotorSpeed(motorSpeed);

  // Debug the froot loops 
  Serial.print(pitch);
  Serial.print(' ');
  Serial.print(pidOutput);
  Serial.print(' ');
  Serial.println(motorSpeed);

  delay(10); // about 100 Hz
}
