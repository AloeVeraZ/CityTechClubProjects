#include <Wire.h>

const int MPU_ADDR = 0x68;   // MPU6050 I2C address

int16_t accX, accY, accZ;
int16_t gyroX, gyroY, gyroZ;

float roll = 0.0f;
float pitch = 0.0f;
float yaw = 0.0f;

unsigned long lastMicros = 0;

void mpuWrite(byte reg, byte data) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

void readMPU() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  accX = (Wire.read() << 8) | Wire.read();
  accY = (Wire.read() << 8) | Wire.read();
  accZ = (Wire.read() << 8) | Wire.read();

  Wire.read(); Wire.read(); // 

  gyroX = (Wire.read() << 8) | Wire.read();
  gyroY = (Wire.read() << 8) | Wire.read();
  gyroZ = (Wire.read() << 8) | Wire.read();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Wake up MPU6050 (PWR_MGMT_1 = 0)
  mpuWrite(0x6B, 0x00);

  // Optional: set gyro full scale +/- 250 deg/s (0x00)
  mpuWrite(0x1B, 0x00);

  // Optional: set accel full scale +/- 2g (0x00)
  mpuWrite(0x1C, 0x00);

  delay(200);
  lastMicros = micros();

  Serial.println("roll pitch yaw"); // header helps label lines 
}

void loop() {
  readMPU();

  unsigned long now = micros();
  float dt = (now - lastMicros) / 1000000.0f;
  lastMicros = now;

  // raw accel to g's 
  float ax = accX / 16384.0f;
  float ay = accY / 16384.0f;
  float az = accZ / 16384.0f;

  //raw gyro to deg/s 
  float gx = gyroX / 131.0f;
  float gy = gyroY / 131.0f;
  float gz = gyroZ / 131.0f;

  // roll and pitrjc
  float accelRoll  = atan2(ay, az) * 180.0f / PI;
  float accelPitch = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0f / PI;

  //  gyro for angles (degrees)
  float gyroRoll  = roll  + gx * dt;
  float gyroPitch = pitch + gy * dt;
  yaw += gz * dt; // yaw will drift without magnetometer (normal)

  // folterrr
  const float alpha = 0.98f;
  roll  = alpha * gyroRoll  + (1.0f - alpha) * accelRoll;
  pitch = alpha * gyroPitch + (1.0f - alpha) * accelPitch;

  // Output for Serial Plotter: three numbers separated by spaces
  Serial.print(roll);  Serial.print(' ');
  Serial.print(pitch); Serial.print(' ');
  Serial.println(yaw);

  delay(10); // ~100 Hz
}
