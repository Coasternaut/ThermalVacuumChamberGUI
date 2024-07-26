const uint8_t TEMP_PINS[] = {A6, A5, A4, A3, A1, A0, A2};
const int NUM_SENSORS = 7;

const float aref_voltage = 3.285;

int input = 0;

void setup() {
  Serial.begin(9600);

  analogReference(EXTERNAL);
}

void loop() {
  // put your main code here, to run repeatedly:

  if (Serial.available() > 0) {
    input = Serial.read();

    if (input == 68){ // ASCII for "D"
      for (int i = 0; i < NUM_SENSORS; i++) {
        Serial.print(convertCelsius(analogRead(TEMP_PINS[i])));
        Serial.print(';');
      }
      Serial.println();
    }
  }
}

float convertCelsius(int reading) {
  float mV = reading * (aref_voltage / 1024.0);
  // Serial.print(mV);
  // Serial.println(" millivolts");

  float celsius = (mV - 0.5) * 100;
  // Serial.print(celsius);
  // Serial.println(" degrees C");

  return celsius;
}
