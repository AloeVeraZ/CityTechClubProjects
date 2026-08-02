#include <Wire.h>
#include <math.h>

// ===================== PICO I2C CONFIG (GP14/15) =====================
#define PIN_SDA 14
#define PIN_SCL 15
arduino::MbedI2C WireMPU(PIN_SDA, PIN_SCL); 
const uint8_t MPU_ADDR = 0x68;

// ===================== MOTOR PINS =====================
const int ENA = 4; const int IN1 = 5; const int IN2 = 6;
const int ENB = 7; const int IN3 = 8; const int IN4 = 9;

// ===================== CONFIGURATION =====================
bool REVERSE_MOTORS = false; 
float targetAngle = -3.0;    
const int MIN_PWM = 150;     
const int MAX_PWM = 255;     

// ===================== PID TUNING =====================
float Kp = 75.0;             
float Ki = 2.0;              
float Kd = 3.0;              

// ===================== STATE VARIABLES =====================
int16_t accX, accY, accZ, gyroX;
float pitch = 0.0;
float gyroOffsetX = 0.0;
unsigned long lastMicros = 0;
unsigned long lastPrint = 0;

float pidError = 0; 
float previousError = 0; 
float integral = 0;

// ===================== MPU HELPERS =====================
void mpuWrite(uint8_t reg, uint8_t data) {
  WireMPU.beginTransmission(MPU_ADDR);
  WireMPU.write(reg);
  WireMPU.write(data);
  WireMPU.endTransmission();
}

void readMPU() {
  WireMPU.beginTransmission(MPU_ADDR);
  WireMPU.write(0x3B);
  WireMPU.endTransmission(false);
  WireMPU.requestFrom(MPU_ADDR, (uint8_t)14);

  if (WireMPU.available() >= 14) {
    accX = (WireMPU.read() << 8) | WireMPU.read();
    accY = (WireMPU.read() << 8) | WireMPU.read();
    accZ = (WireMPU.read() << 8) | WireMPU.read();
    WireMPU.read(); WireMPU.read(); 
    gyroX = (WireMPU.read() << 8) | WireMPU.read(); 
    while(WireMPU.available()) WireMPU.read(); 
  }
}

void setup() {
  Serial.begin(115200);
  WireMPU.begin();
  WireMPU.setClock(1000000); 

  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  mpuWrite(0x6B, 0x00); 
  delay(500);

  long sum = 0;
  for (int i = 0; i < 500; i++) {
    readMPU();
    sum += gyroX;
    delay(2);
  }
  gyroOffsetX = sum / 500.0;
  
  lastMicros = micros();
}

void loop() {
  // 1. 0.5ms Loop Timing
  unsigned long now = micros();
  unsigned long interval = now - lastMicros;
  if (interval < 500) return; 
  
  float dt = interval / 1000000.0f;
  lastMicros = now;

  readMPU();
  float ax = accX / 16384.0f;
  float az = accZ / 16384.0f;
  float gyroRate = (gyroX - gyroOffsetX) / 131.0f;

  float accelPitch = atan2(-ax, abs(az)) * 57.295f; 
  pitch = 0.99f * (pitch + gyroRate * dt) + 0.01f * accelPitch;

  // 2. PID Logic
  if (pitch > 35.0 || pitch < -85.0) {
    stopMotors();
    integral = 0;
    previousError = 0;
  } else {
    pidError = targetAngle - pitch;
    
    // --- ASYMMETRIC BOOST ---
    // If falling in the + direction (forward), we boost the Error
    float effectiveError = pidError;
    if (pidError < 0) { // Robot is tilting Forward (+)
       effectiveError *= 1.4; // 40% more aggressive on the "weak" side
    }

    integral += effectiveError * dt;
    integral = constrain(integral, -150, 150); 
    float derivative = (effectiveError - previousError) / dt;
    
    float output = (Kp * effectiveError) + (Ki * integral) + (Kd * derivative);
    previousError = effectiveError;

    driveMotors(output, abs(effectiveError));
  }

  if (millis() - lastPrint >= 500) {
    Serial.print("Pitch: "); Serial.println(pitch);
    lastPrint = millis();
  }
}

void driveMotors(float speed, float absErr) {
  if (abs(speed) < 0.1) {
    stopMotors();
    return;
  }

  // Map to your 150-255 range
  int pwm = map(constrain(abs(speed), 0, 255), 0, 255, MIN_PWM, MAX_PWM);
  
  // EXTRA PUSH for the + direction
  // If we are tilting positive, we enforce an even higher minimum PWM
  if (pidError < -2.0 && pwm < 185) {
      pwm = 185; 
  }

  bool dir;
  if (REVERSE_MOTORS) { dir = (speed < 0); } 
  else { dir = (speed > 0); }

  digitalWrite(IN1, dir);   digitalWrite(IN2, !dir);
  digitalWrite(IN3, dir);   digitalWrite(IN4, !dir);
  analogWrite(ENA, pwm);    analogWrite(ENB, pwm);
}

void stopMotors() {
  analogWrite(ENA, 0); analogWrite(ENB, 0);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}
