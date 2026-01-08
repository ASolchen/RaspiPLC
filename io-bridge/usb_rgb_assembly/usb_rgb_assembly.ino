#include <Arduino.h>
#include "max6675.h"
#define FRAME_SIZE 256

#define SCK_PIN D8
#define MISO_PIN D12
#define TEMP1_SELECT_PIN D4
#define TEMP2_SELECT_PIN D5
#define HEATER1_PIN D2
#define HEATER2_PIN D3
#define RED_PIN 14
#define GREEN_PIN 15
#define BLUE_PIN 16


typedef struct __attribute__((packed)) {
  uint8_t  watchdog_out;
  uint8_t  heater1;
  uint8_t  heater2;
} out_assembly_t;

typedef struct __attribute__((packed)) {
  uint8_t  watchdog_in;
  double temp1;
  double temp2;
} in_assembly_t;

//create buffers
uint8_t rx_buf[FRAME_SIZE];
uint8_t tx_buf[FRAME_SIZE];
//set pointers of in and out assemblies to the buffers
out_assembly_t *outAsm = (out_assembly_t *)rx_buf;
in_assembly_t  *inAsm  = (in_assembly_t  *)tx_buf;
const uint32_t TIMEOUT_MS = 500;
uint32_t timeout_last;
MAX6675 tc1(SCK_PIN, TEMP1_SELECT_PIN, SCK_PIN);
MAX6675 tc2(SCK_PIN, TEMP2_SELECT_PIN, SCK_PIN);
uint8_t blink;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  //Serial.begin(115200);      // CDC → RaspiPLC / Python
  Serial1.begin(115200);    // UART → Debug console
  //setup pins for pwm
  pinMode(HEATER1_PIN, OUTPUT);
  pinMode(HEATER2_PIN, OUTPUT);
  //setup pins for SPI Chip Selects
  pinMode(TEMP2_SELECT_PIN, OUTPUT);
  pinMode(TEMP2_SELECT_PIN, OUTPUT);
  //init buffers
  memset(rx_buf, 0, sizeof(rx_buf));
  memset(tx_buf, 0, sizeof(tx_buf));
}

void loop() {
  if (0){//Serial.available() >= FRAME_SIZE) {
    timeout_last = millis();   // reset watchdog
    //Serial.readBytes(rx_buf, FRAME_SIZE);
    inAsm->watchdog_in = outAsm->watchdog_out + 1; //send back incremented watchdog
    inAsm->temp1 = tc1.readFahrenheit(); //read SPI
    inAsm->temp2 = tc2.readFahrenheit(); //read SPI
    analogWrite(HEATER1_PIN, outAsm->heater1);
    analogWrite(HEATER2_PIN, outAsm->heater2);
    //Serial.write(tx_buf, FRAME_SIZE);
  }
  else{
    if ((uint32_t)(millis() - timeout_last) > TIMEOUT_MS) {
      // timeout occurred, clear outputs
      analogWrite(HEATER1_PIN, 0x00);
      analogWrite(HEATER2_PIN, 0x00);
      
    }
    delay(10);
    Serial1.println("test");
  }
}
