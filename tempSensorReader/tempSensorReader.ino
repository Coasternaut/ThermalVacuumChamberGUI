#include <movingAvg.h>

const uint8_t TEMP_PINS[] = {A2, A0, A1, A3, A5, A6, A4};
const int NUM_SENSORS = 7;

const long AREF_uV = 3285000;

int input = 0;

bool outputValues = false;

const int LOOP_DELAY_MS = 10;

const int READS_PER_CYCLE = 5;

const int AVERAGE_POINTS = 300;

//movingAvg avgSensorA(averagePoints);
//movingAvg avgSensorB(averagePoints);
//movingAvg avgSensorC(averagePoints);
//movingAvg avgSensorD(averagePoints);
//movingAvg avgSensorE(averagePoints);
//movingAvg avgSensorF(averagePoints);
//movingAvg avgSensorG(averagePoints);

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
    if (input == 82) { // ASCII for "R"  prints raw read average
      for (int i = 0; i < NUM_SENSORS; i++) {
        Serial.print(sensorAvgs[i].getAvg());
        Serial.print(';');
      }
      Serial.println('\r');
    }
    if (input == 65) { // ASCII for "A" prints 5 readings from Sensor A ADC
      for (int i = 0; i < 5; i++) {
        Serial.println(analogRead(TEMP_PINS[0]));
      }
    }
//    if (input == 77) { // ASCII for "M" prints readings in millivolts
//      for (int i = 0; i < NUM_SENSORS; i++) {
//        Serial.print(convert_mV(sensorAvgs[i].getAvg()));
//        Serial.print(';');
//      }
//      Serial.println('\r');
//    }

   input = 0;
 }

  // iterates through all temperature sensors
    for (int i = 0; i < NUM_SENSORS; i++) {

      // adds new reading to rolling average
      for (int j = 0; j < READS_PER_CYCLE; j++) {
        sensorAvgs[i].reading(ADC_to_Celsius100(analogRead(TEMP_PINS[i])));
      }
      
      // prints temperature data if requested
      if (outputValues) {
        Serial.print((sensorAvgs[i].getAvg()) / 100.0);
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
//
//float convertCelsius(int mV) {
//  //float mV = reading * (AREF_VOLTAGE / 1024.0);
//  // Serial.print(mV);
//  // Serial.println(" millivolts");
//
//  float celsius = (mV - 500) / 10.0;
//  // Serial.print(celsius);
//  // Serial.println(" degrees C");
//
//  return celsius;
//}

//long convert_mV(int reading) {
//   (reading * AREF_mV) / 1024;
//}

int ADC_to_Celsius100(int reading) {
  long uV = (reading * AREF_uV) / 1024;
  return (uV - 500000) / 100;
}
