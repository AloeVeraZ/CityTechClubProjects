// Motor B
int ENB = 9;
int IN4 = 8;
int IN3 = 7;

// Motor A
int ENA = 5;
int IN2 = 4;
int IN1 = 2;

void setup() {

  pinMode(ENB, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(IN3, OUTPUT);

  pinMode(ENA, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN1, OUTPUT);
}

void loop() {

  // both fwd
  digitalWrite(IN4, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN1, LOW);

  analogWrite(ENB, 255);
  analogWrite(ENA, 255);

  delay(4000);

  // STOP
  analogWrite(ENB, 0);
  analogWrite(ENA, 0);

  delay(2000);

  // bpoth reverse
  digitalWrite(IN4, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN1, HIGH);

  analogWrite(ENB, 200);
  analogWrite(ENA, 200);

  delay(4000);

  // stop
  analogWrite(ENB, 0);
  analogWrite(ENA, 0);

  delay(3000);
}
