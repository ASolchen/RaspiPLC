#pragma once

#include <Arduino.h>
#include <stdint.h>
#include "pide.h"
#define USB_FRAME_SIZE 256
#define USB_FRAME_MAGIC 0xDEADBEEF



typedef union {
    uint32_t raw;

    struct {
        uint32_t cmd_00 : 1;
        uint32_t cmd_01 : 1;
        uint32_t cmd_02 : 1;// etc.
    } bits;

} usb_comm_cmd_bits_t;


typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_out;
  usb_comm_cmd_bits_t command_bits;
  pide_ctrl_t htr1_pide_ctrl;
} usb_comm_out_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint8_t  watchdog_in;
  uint8_t  pad5; //keep 32-bit alignment
  uint8_t  pad6; //keep 32-bit alignment
  uint8_t  pad7; //keep 32-bit alignment
  float temp1;
  float temp2;
  float heater1;
  float heater2;
  pide_stat_t htr1_pide_stat;
} usb_comm_in_t;
