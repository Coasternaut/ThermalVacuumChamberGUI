const uint8_t TEMP_PINS[] = {A2, A0, A1, A3, A5, A6, A4};
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

      // iterates through all temperature sensors
      for (int i = 0; i < NUM_SENSORS; i++) {

        // averages 10 values a specific sensor
        int averageSum = 0;

        for (int j = 0; j < 10; j++) {
          averageSum += analogRead(TEMP_PINS[i]);
        }
        
        Serial.print(convertCelsius(averageSum / 10));
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
