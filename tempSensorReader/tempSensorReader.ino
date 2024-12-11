#include <movingAvg.h>

const uint8_t TEMP_PINS[] = {A2, A0, A1, A3, A5, A6, A4};
const int NUM_SENSORS = 7;

const long AREF_uV = 3285000;

const long AREF_mV = 3285;

int input = 0;

bool outputValues = false;

const int LOOP_DELAY_MS = 15;

const int READS_PER_CYCLE = 10;

const int AVERAGE_POINTS = 400;

movingAvg sensorAvgs[NUM_SENSORS] = {movingAvg(AVERAGE_POINTS),
                                     movingAvg(AVERAGE_POINTS), 
                                     movingAvg(AVERAGE_POINTS), 
                                     movingAvg(AVERAGE_POINTS),
                                     movingAvg(AVERAGE_POINTS), 
                                     movingAvg(AVERAGE_POINTS),
                                     movingAvg(AVERAGE_POINTS)};

void setup() {
  Serial.begin(9600);

  analogReference(EXTERNAL);

  for (int i = 0; i < NUM_SENSORS; i++) {
    sensorAvgs[i].begin();
  }
}

void loop() {

  // checks if new data is being requested
  if (Serial.available() > 0) {
    input = Serial.read();
    
    if (input == 68) { // ASCII for "D"
      outputValues = true;
    }
    
   input = 0;
 }

  // iterates through all temperature sensors
    for (int i = 0; i < NUM_SENSORS; i++) {

      // adds new reading to rolling average
      for (int j = 0; j < READS_PER_CYCLE; j++) {
        sensorAvgs[i].reading(ADC_to_mCelsius_LM19(analogRead(TEMP_PINS[i])));
      }
      
      // prints temperature data if requested
      if (outputValues) {
        Serial.print((sensorAvgs[i].getAvg()) / 1000.0, 1);
        Serial.print(';');
      }
    }

  // finishes line if printing and resets output flag
  if (outputValues) {
    Serial.println('\r');
    outputValues = false;
  }

  // limits loop speed
  delay(LOOP_DELAY_MS);
}

// converts an ADC reading to Celsius * 1000
int ADC_to_mCelsius(int reading) {
  long uV = (reading * AREF_uV) / 1024;
  return (uV - 500000) / 10;
}

// convert ADC reading to milli Celsius for LM19 Temperature Sensor
int ADC_to_mCelsius_LM19(int reading){
  double V = (reading * AREF_mV / 1000.) / 1024.;
  double temp = -1481.96 + sqrt(2.1962 * pow(10, 6) + ( 1.8639 - V ) / (3.88 * pow(10, -6)));
  return int(temp * 1000);
}
