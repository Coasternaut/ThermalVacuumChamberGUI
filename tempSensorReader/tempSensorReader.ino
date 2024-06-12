const uint8_t TEMP_PINS[] = {A0, A1, A2, A3, A4, A5, A6}; //['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6'];
const int NUM_SENSORS = 7;

const float aref_voltage = 3.305;

void setup() {
  Serial.begin(9600);

  analogReference(EXTERNAL);
}

void loop() {
  // put your main code here, to run repeatedly:

  for (int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(convertCelsius(analogRead(TEMP_PINS[i])));
    Serial.print(';');
  }

  Serial.println();

  delay(1000);

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