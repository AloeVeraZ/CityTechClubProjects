#include <Wire.h>

// ===================== MPU6050 SETTINGS =====================
const int MPU_ADDR = 0x68;
int16_t accX, accY, accZ, gyroY;
float pitch = 0.0f;
unsigned long lastMicros = 0;

// ===================== MOTOR PINS =====================
const int ENA = 5; const int ENB = 6;
const int IN1 = 7; const int IN2 = 8;
const int IN3 = 9; const int IN4 = 10;

// ===================== HIGH-AGGRESSION TUNING =====================
float Kp = 80.0;           
float Ki = 1.2;            
float Kd = 4.8;            
float targetAngle = -2.0;   

const int ABSOLUTE_MAX_PWM = 220; // Your new Max Speed
float deadzone = 0.2;      

// ===================== STATE VARIABLES =====================
float error = 0, previousError = 0, integral = 0;

void setup() {
  Serial.begin(115200); 
  Wire.begin();

  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); Wire.write(0x00);
  Wire.endTransmission();
  
  delay(1000); 
  lastMicros = micros();
}

void loop() {
  // 1. READ SENSOR
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  accX = (Wire.read() << 8) | Wire.read();
  accY = (Wire.read() << 8) | Wire.read();
  accZ = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); 
  Wire.read(); Wire.read(); 
  gyroY = (Wire.read() << 8) | Wire.read();

  // 2. TIMING
  unsigned long now = micros();
  float dt = (now - lastMicros) / 1000000.0f;
  lastMicros = now;
  if (dt <= 0 || dt > 0.05) dt = 0.004;

  // 3. FLIPPED SENSOR MATH
  float accelPitch = atan2((float)-accX, (float)-accZ) * 180.0f / PI;
  float gyroRate = -(gyroY / 131.0f); 
  pitch = 0.995f * (pitch + gyroRate * dt) + 0.005f * accelPitch;

  // 4. PID LOGIC
  if (pitch > 35.0 || pitch < -80.0) { 
    stopMotors();
    integral = 0;
    previousError = 0;
  } else {
    error = targetAngle - pitch;

    if (abs(error) < deadzone) error = 0;

    integral += error * dt;
    integral = constrain(integral, -200, 200); 
    float derivative = (error - previousError) / dt;
    
    float pidOutput = (Kp * error) + (Ki * integral) + (Kd * derivative);
    previousError = error;

    driveMotors(pidOutput, abs(error));
  }

  Serial.print("Angle:"); 
  Serial.println(pitch);
}

void driveMotors(float speed, float absError) {
  float absSpeed = abs(speed);
  if (absSpeed < 0.1) { 
    stopMotors();
    return;
  }

  // --- STEPPED MIN PWM (Your previous logic) ---
  int dynamicMinPWM = 145;
  if (absError >= 10.0)      dynamicMinPWM = 195;
  else if (absError >= 6.0) dynamicMinPWM = 175;
  else if (absError >= 3.0) dynamicMinPWM = 165;

  // --- 12% DECREASE MAX PWM EVERY 5 DEGREES ---
  // 12% reduction = multiply by 0.88
  int dynamicMaxPWM = ABSOLUTE_MAX_PWM;
  
  if (absError < 5.0) {
    dynamicMaxPWM = ABSOLUTE_MAX_PWM * 0.88 * 0.88 * 0.88; // Reduced 3 times
  } 
  else if (absError < 10.0) {
    dynamicMaxPWM = ABSOLUTE_MAX_PWM * 0.88 * 0.88;      // Reduced 2 times
  } 
  else if (absError < 15.0) {
    dynamicMaxPWM = ABSOLUTE_MAX_PWM * 0.88;             // Reduced 1 time
  }

  // Safety check: Ensure Max is never lower than Min
  if (dynamicMaxPWM < dynamicMinPWM) dynamicMaxPWM = dynamicMinPWM + 10;

  // Map the PID to the narrow, aggressive window
  int pwm = map(constrain(absSpeed, 0, 255), 0, 255, dynamicMinPWM, dynamicMaxPWM);
  
  if (speed > 0) {
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  } else {
    digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
  }
  
  analogWrite(ENA, pwm);
  analogWrite(ENB, pwm);
}

void stopMotors() {
  analogWrite(ENA, 0); analogWrite(ENB, 0);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}
