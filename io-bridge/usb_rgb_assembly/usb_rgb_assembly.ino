#include <Arduino.h>
#include "max6675.h"
#include "pide.h"
#define FRAME_SIZE 256
#define MAGIC 0xDEADBEEF

#define SCK_PIN 8
#define MISO_PIN 12
#define TEMP1_SELECT_PIN 4
#define TEMP2_SELECT_PIN 5
#define HEATER1_PIN A7
#define HEATER2_PIN A6
#define RED_PIN 14
#define GREEN_PIN 15
#define BLUE_PIN 16

typedef union {
    uint32_t raw;

    struct {
        uint32_t cmd_00 : 1;
        uint32_t cmd_01 : 1;
        uint32_t cmd_02 : 1;// etc.
    } bits;

} command_bits_t;


typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_out;
  command_bits_t command_bits;
  float setpoint;
} out_assembly_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_in;
  float temp1;
  float temp2;
  float heater1;
  float heater2;
} in_assembly_t;



const uint16_t UPDATE_TM = 50;
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
PIDE tic1(1.0f,0.1f,0.0f,50.0f,400.0f);

PIDE tic2(1.0f,0.1f,0.0f,50.0f,400.0f);
uint8_t blink;
uint8_t comm_ok;
uint8_t task_counter;
uint32_t task_last;

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
  tic1.setSp(200.0);
  tic2.setSp(100.0);
}

void control_loop();
void handle_comms();
void handle_commands();

void loop() {
  handle_comms();
  
  control_loop();
}


void handle_comms(){
  bool magic_ok = true;
  inAsm->magic = MAGIC;
  

  if (Serial.available() >= FRAME_SIZE) {   
    Serial.readBytes(rx_buf, FRAME_SIZE);
    magic_ok = (outAsm->magic == MAGIC);
    if (magic_ok){
      inAsm->watchdog_in = outAsm->watchdog_out + 1; //send back incremented watchdog
      Serial.write(tx_buf, FRAME_SIZE);
      //Serial.flush();
      digitalWrite(RED_PIN, HIGH); //turn off red LED
      digitalWrite(GREEN_PIN, blink); // blink green LED = good comms
      blink = ! blink;
      comm_ok = 1;
      timeout_last = millis();   // reset watchdog
    }
  } else {
      if ((uint32_t)(millis() - timeout_last) > TIMEOUT_MS) {
      // timeout occurred, clear outputs
      comm_ok = 0;
      }
  }
}

void handle_commands(){
  //check command bits and args
}

void control_loop(){
  uint32_t dt;
  uint32_t now = millis();
  dt = now - task_last;
  if (now - task_last >= UPDATE_TM){
    task_last += UPDATE_TM; //reset the timer
    //need to interleave the temp since the MAX6675 need +200mS to update temp
    if(task_counter == 0){
      inAsm->temp1 = tc1.readF();//read SPI
      inAsm->heater1 = tic1.update(inAsm->temp1); //update TIC1 PID
    } 
    if(task_counter == 5){
      inAsm->temp2 = tc2.readF();//read SPI
      inAsm->heater2 = tic2.update(inAsm->temp2); //update TIC1 PID
    } 
    
    //do hmi stuff here
    if(comm_ok){
      handle_commands();
    } else {
      outAsm->command_bits.raw = 0x00; //no comms, clear any bits
      digitalWrite(GREEN_PIN, HIGH); // turn off green LED
      if (task_counter == 0){
        digitalWrite(RED_PIN, blink); //blink red LED = bad comms
        blink = ! blink;
        // Serial.print("Temp2: ");
        // Serial.print(inAsm->temp2);
        // Serial.print(" Dt: ");
        // Serial.println(dt);
      }
    }

    //update the outputs
    analogWrite(HEATER1_PIN, inAsm->heater1);
    analogWrite(HEATER2_PIN, inAsm->heater2);
    task_counter += 1;
    task_counter %= 10;
  }
}

