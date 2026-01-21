// usb_rgb_assembly.ino
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
const uint32_t TIMEOUT_MS = 500;

// Temp Devices
MAX6675 tc1(SCK_PIN, TEMP1_SELECT_PIN, MISO_PIN);
MAX6675 tc2(SCK_PIN, TEMP2_SELECT_PIN, MISO_PIN);

// Assemblies
usb_comm_out_t outAsm;
usb_comm_in_t  inAsm;

// Comms class
UsbComm usb(Serial, &outAsm, &inAsm);

// PID 
PIDE tic1(&inAsm.htr1_pide_stat, &outAsm.htr1_pide_ctrl);

uint8_t blink;
uint8_t task_counter;
uint32_t task_last;

static void handle_commands() {
  tic1.handleCmds();
}

static void control_loop() {
  uint32_t now = millis();
  if ((uint32_t)(now - task_last) >= UPDATE_TM) {
    task_last += UPDATE_TM;

    // Interleave thermocouple reads
    if (task_counter == 0) {
      inAsm.temp1 = tc1.readF();
      tic1.update(inAsm.temp1);

      inAsm.heater1 = inAsm.htr1_pide_stat.Cv;
      inAsm.heater2 = inAsm.htr1_pide_stat.Cv;
    }

    if (task_counter == 5) {
      inAsm.temp2 = tc2.readF();
    }

    if (usb.commOk()) {
      // Only apply host commands when comms are good
      handle_commands();
      digitalWrite(BLUE_PIN, LOW); // solid ON when comm ok
    } else {
      // no comms: safe behavior
      outAsm.command_bits.raw = 0x00;
      digitalWrite(BLUE_PIN, blink);
      blink = !blink;

      if (task_counter == 0) {
        //debug when not reading with python USB
        Serial.print("SP ");  Serial.print(inAsm.htr1_pide_stat.Sp);
        Serial.print(" PV "); Serial.print(inAsm.htr1_pide_stat.Pv);
        Serial.print(" CV "); Serial.print(inAsm.htr1_pide_stat.Cv);
        Serial.print(" ERR ");Serial.print(inAsm.htr1_pide_stat.Err);
        Serial.print(" Temp2 ");Serial.print(inAsm.temp2);
        Serial.println();
      }
    }

    // outputs
    analogWrite(HEATER1_PIN, (int)inAsm.heater1);
    analogWrite(HEATER2_PIN, (int)inAsm.heater2);

    task_counter = (task_counter + 1) % 10;
  }
}

void setup() {
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(HEATER1_PIN, OUTPUT);
  pinMode(HEATER2_PIN, OUTPUT);

  // NOTE: If this is USB CDC, this is fine; if this is UART debug, you likely want a different port.
  Serial.begin(500000);

  usb.begin();
  usb.setTimeoutMs(TIMEOUT_MS);

  // Initialize desired defaults in *outAsm* control fields (host may override later)
  outAsm.htr1_pide_ctrl.setBits  = 0;
  outAsm.htr1_pide_ctrl.set_Sp   = 100.0f;
  outAsm.htr1_pide_ctrl.set_Kp   = 2.0f;
  outAsm.htr1_pide_ctrl.set_Ki   = 0.1f;
  outAsm.htr1_pide_ctrl.set_Kd   = 0.0f;
  outAsm.htr1_pide_ctrl.set_Mode = PID_AUTO;
  outAsm.htr1_pide_ctrl.set_Cv   = 0.0f;
  outAsm.htr1_pide_ctrl.set_PvMin= 0.0f;
  outAsm.htr1_pide_ctrl.set_PvMax= 500.0f;

  // Inbound telemetry defaults
  inAsm.magic = USB_FRAME_MAGIC;
}

void loop() {
  // Poll comms as often as possible
  usb.poll();

  // Control/update loop
  control_loop();
}
