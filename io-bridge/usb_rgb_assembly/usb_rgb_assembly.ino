#include <Arduino.h>
#include "max6675.h"
#include "usb_comm.h"
#include "pide.h"


#define SCK_PIN 18
#define MISO_PIN 19
#define TEMP1_SELECT_PIN 4
#define TEMP2_SELECT_PIN 17
#define HEATER1_PIN 5
#define HEATER2_PIN 26
#define BLUE_PIN 2


const uint16_t UPDATE_TM = 50;
//create buffers
uint8_t rx_buf[USB_FRAME_SIZE];
uint8_t tx_buf[USB_FRAME_SIZE];
//set pointers of in and out assemblies to the buffers
usb_comm_out_t *outAsm = (usb_comm_out_t *)rx_buf;
usb_comm_in_t  *inAsm  = (usb_comm_in_t  *)tx_buf;
const uint32_t TIMEOUT_MS = 500;
uint32_t timeout_last;
MAX6675 tc1(SCK_PIN, TEMP1_SELECT_PIN, MISO_PIN);
MAX6675 tc2(SCK_PIN, TEMP2_SELECT_PIN, MISO_PIN);
PIDE tic1(&inAsm->htr1_pide_stat, &outAsm->htr1_pide_ctrl); //smoker temp control

uint8_t blink;
uint8_t comm_ok;
uint8_t task_counter;
uint32_t task_last;

void setup() {
  pinMode(BLUE_PIN, OUTPUT);
  //Serial.begin(115200);      // CDC → RaspiPLC / Python
  Serial.begin(500000);    // UART → Debug console
  //setup pins for pwm
  pinMode(HEATER1_PIN, OUTPUT);
  pinMode(HEATER2_PIN, OUTPUT);
  //init buffers
  memset(rx_buf, 0x00, sizeof(rx_buf));
  memset(tx_buf, 0x00, sizeof(tx_buf));
  //init PIDE
  outAsm->htr1_pide_ctrl.set_Sp = 100.0;
  outAsm->htr1_pide_ctrl.set_Kp = 2.0;
  outAsm->htr1_pide_ctrl.set_Ki = 0.1;
  outAsm->htr1_pide_ctrl.set_Kd = 0.0;
  outAsm->htr1_pide_ctrl.set_Mode = PID_AUTO;
  outAsm->htr1_pide_ctrl.set_Cv = 0.0;
  outAsm->htr1_pide_ctrl.set_PvMin = 0.0;
  outAsm->htr1_pide_ctrl.set_PvMax = 500.0;

}

void control_loop();
void handle_comms();
void handle_commands();

void loop() {
  handle_comms();
  handle_commands();
  control_loop();
}


void handle_comms(){
  bool magic_ok = true;
  inAsm->magic = USB_FRAME_MAGIC;
  if (Serial.available() >= USB_FRAME_SIZE) {   
    Serial.readBytes(rx_buf, USB_FRAME_SIZE);
    magic_ok = (outAsm->magic == USB_FRAME_MAGIC);
    if (magic_ok){
      inAsm->watchdog_in = outAsm->watchdog_out + 1; //send back incremented watchdog
      Serial.write(tx_buf, USB_FRAME_SIZE);
      digitalWrite(BLUE_PIN, LOW); //turn on blue LED
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
  tic1.handleCmds();
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
      //outAsm->htr1_pide_ctrl.setBits = 64;
      tic1.update(inAsm->temp1); //update TIC1 PID
      inAsm->htr1_pide_stat.Pv = outAsm->htr1_pide_ctrl.set_Kp;
      inAsm->heater1 = inAsm->htr1_pide_stat.Cv;
      inAsm->heater2 = inAsm->htr1_pide_stat.Cv;
    } 
    if(task_counter == 5){
      inAsm->temp2 = tc2.readF();//read SPI
    } 
    
    //do hmi stuff here
    if(comm_ok){
      handle_commands();
    } else {
      outAsm->command_bits.raw = 0x00; //no comms, clear any bits
      if (task_counter == 0){
        digitalWrite(BLUE_PIN, blink); //blink blue LED = no / bad usb comms
        blink = ! blink;
        Serial.print("SP ");
        Serial.print(inAsm->htr1_pide_stat.Sp);
        Serial.print(" PV ");
        Serial.print(inAsm->htr1_pide_stat.Pv);
        Serial.print(" CV ");
        Serial.print(inAsm->htr1_pide_stat.Cv);
        Serial.print(" ERR ");
        Serial.print(inAsm->htr1_pide_stat.Err);
        Serial.print(" Temp 2 ");
        Serial.print(inAsm->temp2);
        Serial.println("");

      }
    }

    //update the outputs
    analogWrite(HEATER1_PIN, inAsm->heater1);
    analogWrite(HEATER2_PIN, inAsm->heater2);
    task_counter += 1;
    task_counter %= 10;
  }
}

