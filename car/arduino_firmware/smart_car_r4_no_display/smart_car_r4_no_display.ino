/*
  Smart AI Car - Arduino UNO R4 WiFi firmware PLUS
  NO OLED + NO Freenove 8 RGB LED + NO speaker/amplifier version.

  Added:
  - Motor battery voltage/percent telemetry via voltage divider on A3
  - BEEP command for one short beep on wrong face
  - 2 servo motors: camera pan + HC-SR04 pan
  - Keeps motor/sensor safety logic

  Safety:
  - Motor power must go to TB6612 VM, not Arduino 5V.
  - Arduino GND, motor battery GND, TB6612 GND must be common.
  - Raspberry Pi connects to Arduino by USB only. Do not wire Arduino 5V GPIO to Pi GPIO.
  - If reading motor battery on A3, use a resistor divider. Do NOT connect motor battery + directly to A3.
*/

#include <Wire.h>
#include <Servo.h>

// ===== PIN MAP =====
const int ENC_LEFT_PIN  = 2;
const int ENC_RIGHT_PIN = 3;

const int LEFT_IN1  = 4;
const int LEFT_PWM  = 5;
const int RIGHT_PWM = 6;
const int LEFT_IN2  = 7;
const int RIGHT_IN1 = 8;
const int RIGHT_IN2 = 9;
const int STBY_PIN  = 10;

const int ACTIVE_BUZZER_PIN = 11;  // recommended: drive buzzer through NPN transistor
const int CAM_SERVO_PIN = 12;      // camera pan servo signal
const int IR_OBSTACLE_PIN = 13;    // IR obstacle digital output

const int US_TRIG_PIN = A0;
const int US_ECHO_PIN = A1;
const int EMERGENCY_PIN = A2;      // button to GND, INPUT_PULLUP
const int MOTOR_BAT_PIN = A3;      // motor battery through voltage divider
const int US_SERVO_PIN = A4;       // HC-SR04 pan servo signal

// ===== CONFIG =====
bool LEFT_INVERT = false;
bool RIGHT_INVERT = false;
bool IR_ACTIVE_LOW = true;         // if IR status is reversed, change this

const float WHEEL_DIAMETER_M = 0.065; // change to your wheel diameter
const int PULSES_PER_REV = 20;        // change to your encoder disk slots
const int MAX_PWM = 220;              // soft limit
const int OBSTACLE_STOP_CM = 12;
const int SERVO_MIN_ANGLE = 15;
const int SERVO_MAX_ANGLE = 165;
const int SERVO_CENTER_ANGLE = 90;

// Motor battery voltage divider, default: motor+ -> 100k -> A3 -> 47k -> GND
// This keeps A3 safe even with motor batteries around 6-12V. Adjust if your resistors differ.
const float ADC_REF_V = 5.0;
const float BAT_R_TOP = 100000.0;
const float BAT_R_BOTTOM = 47000.0;
// Adjust these to your motor battery type:
// 2 x AA: empty≈2.0, full≈3.2. 4 x AA: empty≈4.8, full≈6.4. 2 x 18650: empty≈6.4, full≈8.4.
const float MOTOR_BAT_EMPTY_V = 4.8;
const float MOTOR_BAT_FULL_V  = 6.4;

// GY-87 usually contains MPU6050 at address 0x68
const uint8_t MPU_ADDR = 0x68;
bool mpuOK = false;
float lastAccMag = 1.0;
unsigned long lastMpuMs = 0;

volatile unsigned long pulseLeft = 0;
volatile unsigned long pulseRight = 0;

Servo camServo;
Servo usServo;
int camAngle = SERVO_CENTER_ANGLE;
int usAngle = SERVO_CENTER_ANGLE;

bool unlocked = false;
bool emergency = false;
bool alarmActive = false;
bool beepActive = false;
bool tiltWarning = false;
bool impactWarning = false;
String modeName = "LOCKED";

float rpmL = 0, rpmR = 0;
float speedL = 0, speedR = 0, speedAvg = 0;
float distanceCm = -1;
bool irObstacle = false;
float motorBatV = 0.0;
float motorBatPct = 0.0;

unsigned long lastCommandMs = 0;
unsigned long lastTelemetryMs = 0;
unsigned long lastSpeedMs = 0;
unsigned long alarmUntilMs = 0;
unsigned long beepUntilMs = 0;

void isrLeft() { pulseLeft++; }
void isrRight() { pulseRight++; }

int clampAngle(int angle) {
  if (angle < SERVO_MIN_ANGLE) return SERVO_MIN_ANGLE;
  if (angle > SERVO_MAX_ANGLE) return SERVO_MAX_ANGLE;
  return angle;
}

void setCameraServo(int angle) {
  camAngle = clampAngle(angle);
  camServo.write(camAngle);
}

void setUltrasonicServo(int angle) {
  usAngle = clampAngle(angle);
  usServo.write(usAngle);
}

void setBothServos(int angle) {
  angle = clampAngle(angle);
  setCameraServo(angle);
  setUltrasonicServo(angle);
}


int clampPWM(int v) {
  if (v > MAX_PWM) return MAX_PWM;
  if (v < -MAX_PWM) return -MAX_PWM;
  return v;
}

void setSide(int pwmPin, int in1Pin, int in2Pin, int speedVal, bool invert) {
  speedVal = clampPWM(speedVal);
  if (invert) speedVal = -speedVal;

  if (speedVal > 0) {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, speedVal);
  } else if (speedVal < 0) {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
    analogWrite(pwmPin, -speedVal);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, 0);
  }
}

void stopMotors() {
  setSide(LEFT_PWM, LEFT_IN1, LEFT_IN2, 0, LEFT_INVERT);
  setSide(RIGHT_PWM, RIGHT_IN1, RIGHT_IN2, 0, RIGHT_INVERT);
}

bool forwardBlocked(int left, int right) {
  bool forward = (left > 0 && right > 0);
  if (!forward) return false;
  if (distanceCm > 0 && distanceCm < OBSTACLE_STOP_CM) return true;
  if (irObstacle) return true;
  return false;
}

void driveMotors(int left, int right) {
  if (!unlocked || emergency || alarmActive || tiltWarning || impactWarning) {
    stopMotors();
    return;
  }
  if (forwardBlocked(left, right)) {
    stopMotors();
    return;
  }
  digitalWrite(STBY_PIN, HIGH);
  setSide(LEFT_PWM, LEFT_IN1, LEFT_IN2, left, LEFT_INVERT);
  setSide(RIGHT_PWM, RIGHT_IN1, RIGHT_IN2, right, RIGHT_INVERT);
}

float readDistanceCm() {
  digitalWrite(US_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(US_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(US_TRIG_PIN, LOW);
  unsigned long dur = pulseIn(US_ECHO_PIN, HIGH, 25000UL);
  if (dur == 0) return -1;
  return dur / 58.0;
}

void updateMotorBattery() {
  int raw = analogRead(MOTOR_BAT_PIN); // UNO R4 analogRead default 0-1023
  float pinV = raw * ADC_REF_V / 1023.0;
  motorBatV = pinV * (BAT_R_TOP + BAT_R_BOTTOM) / BAT_R_BOTTOM;
  motorBatPct = (motorBatV - MOTOR_BAT_EMPTY_V) * 100.0 / (MOTOR_BAT_FULL_V - MOTOR_BAT_EMPTY_V);
  if (motorBatPct < 0) motorBatPct = 0;
  if (motorBatPct > 100) motorBatPct = 100;
}

void updateSpeed() {
  unsigned long now = millis();
  if (now - lastSpeedMs < 500) return;
  float dt = (now - lastSpeedMs) / 1000.0;
  lastSpeedMs = now;

  noInterrupts();
  unsigned long pL = pulseLeft;
  unsigned long pR = pulseRight;
  pulseLeft = 0;
  pulseRight = 0;
  interrupts();

  rpmL = (pL / (float)PULSES_PER_REV) * (60.0 / dt);
  rpmR = (pR / (float)PULSES_PER_REV) * (60.0 / dt);
  float circumference = 3.1415926 * WHEEL_DIAMETER_M;
  speedL = circumference * rpmL / 60.0;
  speedR = circumference * rpmR / 60.0;
  speedAvg = (speedL + speedR) / 2.0;
}

bool i2cDevicePresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

void initMPU6050() {
  mpuOK = i2cDevicePresent(MPU_ADDR);
  if (!mpuOK) {
    Serial.println("WARN MPU6050_NOT_FOUND");
    return;
  }
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1
  Wire.write(0x00); // wake up
  Wire.endTransmission(true);
  Serial.println("OK MPU6050_FOUND");
}

bool readMPUAccel(float &ax, float &ay, float &az) {
  if (!mpuOK) return false;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, (uint8_t)6) != 6) return false;
  int16_t rawX = (Wire.read() << 8) | Wire.read();
  int16_t rawY = (Wire.read() << 8) | Wire.read();
  int16_t rawZ = (Wire.read() << 8) | Wire.read();
  ax = rawX / 16384.0;
  ay = rawY / 16384.0;
  az = rawZ / 16384.0;
  return true;
}

void updateMPU() {
  if (millis() - lastMpuMs < 120) return;
  lastMpuMs = millis();
  float ax, ay, az;
  if (!readMPUAccel(ax, ay, az)) return;
  float mag = sqrt(ax*ax + ay*ay + az*az);

  tiltWarning = (abs(az) < 0.45 || abs(ax) > 0.90 || abs(ay) > 0.90);
  if (abs(mag - lastAccMag) > 1.25) impactWarning = true;
  lastAccMag = mag;
}

void startAlarm(int seconds) {
  alarmActive = true;
  alarmUntilMs = millis() + (unsigned long)seconds * 1000UL;
  stopMotors();
}

void startBeep(int ms) {
  if (ms < 20) ms = 20;
  if (ms > 2000) ms = 2000;
  beepActive = true;
  beepUntilMs = millis() + (unsigned long)ms;
  digitalWrite(ACTIVE_BUZZER_PIN, HIGH);
}

void updateBuzzer() {
  if (beepActive) {
    if (millis() > beepUntilMs) {
      beepActive = false;
      digitalWrite(ACTIVE_BUZZER_PIN, LOW);
    }
    return;
  }
  if (!alarmActive) {
    digitalWrite(ACTIVE_BUZZER_PIN, LOW);
    return;
  }
  if (millis() > alarmUntilMs) {
    alarmActive = false;
    digitalWrite(ACTIVE_BUZZER_PIN, LOW);
    return;
  }
  bool on = ((millis() / 180) % 2) == 0;
  digitalWrite(ACTIVE_BUZZER_PIN, on ? HIGH : LOW);
}

void sendTelemetry() {
  Serial.print("{\"speedL\":"); Serial.print(speedL, 3);
  Serial.print(",\"speedR\":"); Serial.print(speedR, 3);
  Serial.print(",\"speed\":"); Serial.print(speedAvg, 3);
  Serial.print(",\"speedMpm\":"); Serial.print(speedAvg * 60.0, 2);
  Serial.print(",\"rpmL\":"); Serial.print(rpmL, 1);
  Serial.print(",\"rpmR\":"); Serial.print(rpmR, 1);
  Serial.print(",\"dist\":"); Serial.print(distanceCm, 1);
  Serial.print(",\"ir\":"); Serial.print(irObstacle ? 1 : 0);
  Serial.print(",\"emg\":"); Serial.print(emergency ? 1 : 0);
  Serial.print(",\"tilt\":"); Serial.print(tiltWarning ? 1 : 0);
  Serial.print(",\"impact\":"); Serial.print(impactWarning ? 1 : 0);
  Serial.print(",\"mpuOK\":"); Serial.print(mpuOK ? 1 : 0);
  Serial.print(",\"motorBatV\":"); Serial.print(motorBatV, 2);
  Serial.print(",\"motorBatPct\":"); Serial.print(motorBatPct, 0);
  Serial.print(",\"camAngle\":"); Serial.print(camAngle);
  Serial.print(",\"usAngle\":"); Serial.print(usAngle);
  Serial.print(",\"arduinoLocked\":"); Serial.print(unlocked ? 0 : 1);
  Serial.println("}");
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;
  lastCommandMs = millis();

  if (cmd == "UNLOCK") {
    unlocked = true;
    emergency = false;
    tiltWarning = false;
    impactWarning = false;
    modeName = "WEB";
    Serial.println("OK UNLOCK");
    return;
  }
  if (cmd == "LOCK") {
    unlocked = false;
    modeName = "LOCKED";
    stopMotors();
    Serial.println("OK LOCK");
    return;
  }
  if (cmd == "RESET_WARN") {
    tiltWarning = false;
    impactWarning = false;
    emergency = false;
    Serial.println("OK RESET_WARN");
    return;
  }
  if (cmd == "S" || cmd == "STOP") {
    stopMotors();
    if (unlocked && modeName != "VOICE") modeName = "WEB";
    Serial.println("OK STOP");
    return;
  }
  if (cmd.startsWith("MODE ")) {
    modeName = cmd.substring(5);
    Serial.print("OK MODE "); Serial.println(modeName);
    return;
  }
  if (cmd.startsWith("BEEP")) {
    int ms = 140;
    int sp = cmd.indexOf(' ');
    if (sp > 0) ms = cmd.substring(sp+1).toInt();
    startBeep(ms);
    Serial.println("OK BEEP");
    return;
  }
  if (cmd.startsWith("ALARM")) {
    int sec = 5;
    int sp = cmd.indexOf(' ');
    if (sp > 0) sec = cmd.substring(sp+1).toInt();
    if (sec <= 0) sec = 5;
    startAlarm(sec);
    Serial.println("OK ALARM");
    return;
  }
  if (cmd.startsWith("SERVO ")) {
    int p1 = cmd.indexOf(' ');
    int p2 = cmd.indexOf(' ', p1 + 1);
    if (p2 < 0) { Serial.println("ERR SERVO format"); return; }
    String target = cmd.substring(p1 + 1, p2);
    target.toUpperCase();
    int angle = cmd.substring(p2 + 1).toInt();
    angle = clampAngle(angle);
    if (target == "CAM") {
      setCameraServo(angle);
      Serial.print("OK SERVO CAM "); Serial.println(camAngle);
      return;
    }
    if (target == "US") {
      setUltrasonicServo(angle);
      Serial.print("OK SERVO US "); Serial.println(usAngle);
      return;
    }
    if (target == "BOTH") {
      setBothServos(angle);
      Serial.print("OK SERVO BOTH "); Serial.println(angle);
      return;
    }
    Serial.println("ERR SERVO target");
    return;
  }
  if (cmd.startsWith("LOOK ")) {
    String where = cmd.substring(5);
    where.toUpperCase();
    if (where == "LEFT") {
      setBothServos(150);
      Serial.println("OK LOOK LEFT");
      return;
    }
    if (where == "RIGHT") {
      setBothServos(30);
      Serial.println("OK LOOK RIGHT");
      return;
    }
    if (where == "CENTER" || where == "CENTRE") {
      setBothServos(SERVO_CENTER_ANGLE);
      Serial.println("OK LOOK CENTER");
      return;
    }
    Serial.println("ERR LOOK target");
    return;
  }
  if (cmd.startsWith("D ")) {
    int p1 = cmd.indexOf(' ');
    int p2 = cmd.indexOf(' ', p1 + 1);
    if (p2 < 0) { Serial.println("ERR D format"); return; }
    int left = cmd.substring(p1+1, p2).toInt();
    int right = cmd.substring(p2+1).toInt();
    driveMotors(left, right);
    Serial.println("OK D");
    return;
  }
  Serial.println("ERR UNKNOWN");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LEFT_IN1, OUTPUT); pinMode(LEFT_IN2, OUTPUT); pinMode(LEFT_PWM, OUTPUT);
  pinMode(RIGHT_IN1, OUTPUT); pinMode(RIGHT_IN2, OUTPUT); pinMode(RIGHT_PWM, OUTPUT);
  pinMode(STBY_PIN, OUTPUT);
  digitalWrite(STBY_PIN, HIGH);

  pinMode(ACTIVE_BUZZER_PIN, OUTPUT);
  digitalWrite(ACTIVE_BUZZER_PIN, LOW);
  pinMode(IR_OBSTACLE_PIN, INPUT);
  pinMode(US_TRIG_PIN, OUTPUT);
  pinMode(US_ECHO_PIN, INPUT);
  pinMode(EMERGENCY_PIN, INPUT_PULLUP);
  pinMode(MOTOR_BAT_PIN, INPUT);

  pinMode(ENC_LEFT_PIN, INPUT_PULLUP);
  pinMode(ENC_RIGHT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_LEFT_PIN), isrLeft, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_RIGHT_PIN), isrRight, RISING);

  camServo.attach(CAM_SERVO_PIN);
  usServo.attach(US_SERVO_PIN);
  setBothServos(SERVO_CENTER_ANGLE);

  Wire.begin();
  initMPU6050();

  stopMotors();
  lastSpeedMs = millis();
  lastCommandMs = millis();
  Serial.println("SMART_CAR_R4_PLUS_READY");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handleCommand(cmd);
  }

  emergency = digitalRead(EMERGENCY_PIN) == LOW;
  if (emergency) stopMotors();

  int irRaw = digitalRead(IR_OBSTACLE_PIN);
  irObstacle = IR_ACTIVE_LOW ? (irRaw == LOW) : (irRaw == HIGH);

  static unsigned long lastDistMs = 0;
  if (millis() - lastDistMs > 120) {
    lastDistMs = millis();
    distanceCm = readDistanceCm();
  }

  static unsigned long lastBatMs = 0;
  if (millis() - lastBatMs > 700) {
    lastBatMs = millis();
    updateMotorBattery();
  }

  updateSpeed();
  updateMPU();

  if (millis() - lastCommandMs > 1200) stopMotors();
  if (tiltWarning || impactWarning) stopMotors();

  updateBuzzer();

  if (millis() - lastTelemetryMs > 250) {
    lastTelemetryMs = millis();
    sendTelemetry();
  }
}
