#include <Arduino.h>
#include "max6675.h"
#define FRAME_SIZE 256
#define MAGIC 0xDEADBEEF

#define SCK_PIN 8
#define MISO_PIN 12
#define TEMP1_SELECT_PIN 4
#define TEMP2_SELECT_PIN 5
#define HEATER1_PIN 2
#define HEATER2_PIN 3
#define RED_PIN 14
#define GREEN_PIN 15
#define BLUE_PIN 16
#define UPDATE_TM 50


typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_out;
  uint8_t  heater1;
  uint8_t  heater2;
} out_assembly_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_in;
  float temp1;
  float temp2;
} in_assembly_t;

//create buffers
uint8_t rx_buf[FRAME_SIZE];
uint8_t tx_buf[FRAME_SIZE];
//set pointers of in and out assemblies to the buffers
out_assembly_t *outAsm = (out_assembly_t *)rx_buf;
in_assembly_t  *inAsm  = (in_assembly_t  *)tx_buf;
const uint32_t TIMEOUT_MS = 500;
uint32_t timeout_last;
MAX6675 tc1(SCK_PIN, TEMP1_SELECT_PIN, MISO_PIN);
MAX6675 tc2(SCK_PIN, TEMP2_SELECT_PIN, MISO_PIN);
uint8_t blink;
uint8_t task_counter;
uint16_t task_last;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  //Serial.begin(115200);      // CDC → RaspiPLC / Python
  Serial.begin(15000000);    // UART → Debug console
  //setup pins for pwm
  pinMode(HEATER1_PIN, OUTPUT);
  pinMode(HEATER2_PIN, OUTPUT);
  //setup pins for SPI Chip Selects
  pinMode(TEMP2_SELECT_PIN, OUTPUT);
  pinMode(TEMP2_SELECT_PIN, OUTPUT);
  //init buffers
  memset(rx_buf, 0x00, sizeof(rx_buf));
  memset(tx_buf, 0x00, sizeof(tx_buf));
}

void control_loop();
void handle_comms();

void loop() {
  handle_comms();
  control_loop();
}


void handle_comms(){
  inAsm->magic = MAGIC;
  inAsm->watchdog_in = outAsm->watchdog_out + 1; //send back incremented watchdog

  if (Serial.available() >= FRAME_SIZE) {   
    Serial.readBytes(rx_buf, FRAME_SIZE);
    if (outAsm->magic != MAGIC) {
      //bad read, clear commands
    }
    Serial.write(tx_buf, FRAME_SIZE);
    Serial.flush();
    digitalWrite(RED_PIN, HIGH);
    digitalWrite(GREEN_PIN, blink);
    blink = ! blink;
    timeout_last = millis();   // reset watchdog
  } else {
      if ((uint32_t)(millis() - timeout_last) > TIMEOUT_MS) {
      // timeout occurred, clear outputs
      outAsm->heater1 = 0;
      outAsm->heater2 = 0;
      digitalWrite(RED_PIN, blink);
      digitalWrite(GREEN_PIN, HIGH);
      delay(200);
      blink = ! blink;
      }
  }
}


void control_loop(){
  if ((millis() - task_last) > UPDATE_TM){
    task_last = millis(); //reset the timer
    //need to interleave the temp since the MAX6675 need +200mS to update temp
    if(task_counter == 0){ inAsm->temp1 = tc1.readFahrenheit();} //read SPI;
    if(task_counter == 5){ inAsm->temp2 = tc2.readFahrenheit();} //read SPI;
    //do plc (PID) stuff here
    //update the outputs
    analogWrite(HEATER1_PIN, 0.0);
    analogWrite(HEATER2_PIN, 0.0);
    task_counter += 1;
    task_counter %= 10;
  }
}

