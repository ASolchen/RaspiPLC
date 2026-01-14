#pragma once

#include <Arduino.h>
#include <stdint.h>

#ifndef USB_FRAME_SIZE
#define USB_FRAME_SIZE 256
#endif

class USBComm {
public:
  USBComm();

  // Call once from setup()
  void begin();

  // Call frequently from loop()
  void update();

  // Public buffers (overlay your structs here)
  uint8_t* rxBuf() { return _rx_buf; }
  uint8_t* txBuf() { return _tx_buf; }

  // Status
  bool connected() const { return _connected; }
  bool rxNew() const { return _rx_new; }
  void clearRxNew() { _rx_new = false; }

  uint32_t rxCount() const { return _rx_count; }
  uint32_t txCount() const { return _tx_count; }

  // Optional: throttle IN reports (ms). Default 0 = send whenever update() runs and USB ready.
  void setTxPeriodMs(uint32_t ms) { _tx_period_ms = ms; }

  uint8_t  _rx_buf[USB_FRAME_SIZE];
  uint8_t  _tx_buf[USB_FRAME_SIZE];
  friend void _usbcomm_on_out_report(const uint8_t* data, uint16_t len);


  volatile bool _rx_new;
  bool     _connected;
  uint32_t _rx_count;
  uint32_t _tx_count;

  uint32_t _tx_period_ms;
  uint32_t _last_tx_ms;
};
