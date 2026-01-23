// usb_rgb_assembly.ino
#include <Arduino.h>
#include "max6675.h"
#include "usb_comm.h"
#include "temp_ctrl.h"

// ---------------- Pins ----------------
#define SCK_PIN 18
#define MISO_PIN 19
#define TEMP1_SELECT_PIN 4
#define TEMP2_SELECT_PIN 17
#define HEATER1_PIN 15
#define HEATER2_PIN 16
#define BLUE_PIN 2

// ---------------- Timing ----------------
static const uint16_t UPDATE_TM = 50;      // ms
static const uint32_t TIMEOUT_MS = 500;    // ms "comms active" watchdog

// ---------------- Temp Devices ----------------
MAX6675 tc1(SCK_PIN, TEMP1_SELECT_PIN, MISO_PIN);
MAX6675 tc2(SCK_PIN, TEMP2_SELECT_PIN, MISO_PIN);

// ---------------- Temp Controller that uses the PID ----------------

TempCtrl tic1;


// ---------------- Control Loop State ----------------
uint8_t  blink = 0;
uint8_t  task_counter = 0;
uint32_t task_last = 0;

// ---------------- Comms Activity Tracking ----------------
static uint32_t last_cmd_ms = 0;
static bool comm_ok = false;

// ---------------- Object IDs ----------------
// Keep these aligned with your host-side object IDs.
// With the UsbComm handler-table approach, object_id is used as an index.
static const uint8_t OBJ_NONE = 0;
static const uint8_t OBJ_TIC1 = 1;

// ---------------- USB Command Handlers ----------------
// Adapter: UsbComm::CmdView -> PIDE::handle_cmd()
static bool tic1_usb_handler(const UsbComm::CmdView& cmd,
                            uint8_t* out_payload,
                            uint16_t out_max,
                            uint16_t* out_len)
{
  // Build a PID-local view (PID does NOT know about USB framing)
  pid_cmd_view_t pcmd;
  pcmd.cmd_id = cmd.cmd_id;
  pcmd.payload = cmd.payload;
  pcmd.payload_len = cmd.payload_len;

  pid_cmd_result_t r = tic1.handle_cmd(pcmd, out_payload, out_max, out_len);

  // Return "handled" boolean to UsbComm.
  // In this design, we return true when the command was recognized and processed.
  // You can still encode error details in payload if you want later.
  return (r == PID_CMD_OK);
}

// Handler table (index = object_id). Size must cover the max object id you will use + 1.
static UsbComm::HandlerFn handlers[] = {
  nullptr,          // 0 = OBJ_NONE
  tic1_usb_handler, // 1 = OBJ_TIC1
};

// UsbComm instance
UsbComm usb(Serial, handlers, sizeof(handlers) / sizeof(handlers[0]));

// ---------------- Helpers ----------------
static void control_loop()
{
  uint32_t now = millis();
  if ((uint32_t)(now - task_last) < UPDATE_TM) return;
  task_last += UPDATE_TM;

  // Interleave thermocouple reads
  float temp1 = tic1.pid.stat.Pv; // default (avoid unused warning)
  if (task_counter == 0) {
    temp1 = tc1.readF();
    tic1.update(temp1);

    // Outputs derived from PID CV (0..100). Map to PWM as you like.
    // Here we just pass through as "percent" then scale below.
  }

  // Read temp2 occasionally (not part of PID in this snippet)
  static float temp2 = 0.0f;
  if (task_counter == 5) {
    temp2 = tc2.readF();
  }

  // Comms watchdog LED behavior
  comm_ok = ((uint32_t)(now - last_cmd_ms) <= TIMEOUT_MS);
  if (comm_ok) {
    digitalWrite(BLUE_PIN, blink);     // blink when comms active
  } else {
    digitalWrite(BLUE_PIN, LOW);   // OFF when no comms active
    blink = !blink;
  }

  // Convert PID CV (0..100) -> PWM (0..255)
  float cv = tic1.pid.stat.Cv;
  if (cv < 0.0f) cv = 0.0f;
  if (cv > 100.0f) cv = 100.0f;

  int pwm = (int)(cv * 2.55f + 0.5f);
  if (pwm < 0) pwm = 0;
  if (pwm > 255) pwm = 255;

  analogWrite(HEATER1_PIN, pwm);
  analogWrite(HEATER2_PIN, pwm);

  // Optional: if you want temps visible via READ_STATUS later,
  // you can include them in the PID status or create a separate object.
  // For now, PID status is exactly pide_stat_t.

  task_counter = (task_counter + 1) % 10;
}

void setup()
{
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(HEATER1_PIN, OUTPUT);
  pinMode(HEATER2_PIN, OUTPUT);
  

  // USB CDC serial (ESP32-Sx / TinyUSB CDC) ignores baud, but harmless.
  Serial.begin(500000);
  last_cmd_ms = millis();
  tic1.Mode = TC_PGM_AUTO;
  tic1.Sp = 200.0;
}

void loop()
{
  // Process at most one command per poll() call.
  // If a command is processed and a response is written, poll() returns true.
  if (usb.poll()) {
    last_cmd_ms = millis();
  }

  // Run control loop continuously
  control_loop();
}
