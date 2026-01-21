#pragma once

#include <Arduino.h>
#include <stdint.h>
#include <string.h>
#include "pide.h"

#define USB_FRAME_SIZE       256
#define USB_RX_BUFFER_SIZE   (USB_FRAME_SIZE * 8)
#define USB_FRAME_MAGIC      0xDEADBEEF


typedef union {
    uint32_t raw;
    struct {
        uint32_t cmd_00 : 1;
        uint32_t cmd_01 : 1;
        uint32_t cmd_02 : 1;
    } bits;
} usb_comm_cmd_bits_t;


// --------------------
// OUT (Host → ESP)
// --------------------
typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t  watchdog_out;
    uint8_t  _pad05;
    uint8_t  _pad06;
    uint8_t  _pad07;
    usb_comm_cmd_bits_t command_bits;
    pide_ctrl_t htr1_pide_ctrl;

    uint8_t _reserved[
        USB_FRAME_SIZE -
        (4 + 1 + 3 + sizeof(usb_comm_cmd_bits_t) + sizeof(pide_ctrl_t))
    ];
} usb_comm_out_t;


// --------------------
// IN (ESP → Host)
// --------------------
typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t  watchdog_in;
    uint8_t  _pad05;
    uint8_t  _pad06;
    uint8_t  _pad07;

    float temp1;
    float temp2;
    float heater1;
    float heater2;

    pide_stat_t htr1_pide_stat;

    uint8_t _reserved[
        USB_FRAME_SIZE -
        (4 + 1 + 3 + 4*4 + sizeof(pide_stat_t))
    ];
} usb_comm_in_t;


// --------------------
// UsbComm class
// --------------------
class UsbComm {
public:
    UsbComm(Stream& serial, usb_comm_out_t* outAsm, usb_comm_in_t* inAsm);

    void begin();
    bool poll();                 // ← consumes AT MOST ONE frame
    bool commOk() const;

    void setTimeoutMs(uint32_t ms);

private:
    Stream& s_;
    usb_comm_out_t* out_;
    usb_comm_in_t*  in_;

    uint8_t rx_buf_[USB_RX_BUFFER_SIZE];
    size_t  rx_head_ = 0;

    bool     comm_ok_ = false;
    uint32_t last_rx_ms_ = 0;
    uint32_t timeout_ms_ = 500;

    void readAvailable_();
    bool tryExtractOneFrame_();   // ← exactly ONE frame max
    void consume_(size_t start, size_t len);
    void updateTimeout_();
};
