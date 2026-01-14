#include "usb_comm.h"

extern "C" {
#include "tusb.h"
}

// --------- HID Report Descriptor (Vendor-defined, 256B IN + 256B OUT) ---------
// No report IDs. Report length fixed at 256 bytes each direction.
static const uint8_t hid_report_desc[] = {
  0x06, 0x00, 0xFF,        // Usage Page (Vendor Defined 0xFF00)
  0x09, 0x01,              // Usage (0x01)
  0xA1, 0x01,              // Collection (Application)

  // OUT report (Host -> Device)
  0x09, 0x02,              //   Usage (0x02)
  0x15, 0x00,              //   Logical Min (0)
  0x26, 0xFF, 0x00,        //   Logical Max (255)
  0x75, 0x08,              //   Report Size (8)
  0x95, USB_FRAME_SIZE,    //   Report Count (256)
  0x91, 0x02,              //   Output (Data,Var,Abs)

  // IN report (Device -> Host)
  0x09, 0x03,              //   Usage (0x03)
  0x15, 0x00,              //   Logical Min (0)
  0x26, 0xFF, 0x00,        //   Logical Max (255)
  0x75, 0x08,              //   Report Size (8)
  0x95, USB_FRAME_SIZE,    //   Report Count (256)
  0x81, 0x02,              //   Input (Data,Var,Abs)

  0xC0                     // End Collection
};

// TinyUSB calls this to get the HID report descriptor.
extern "C" uint8_t const* tud_hid_descriptor_report_cb(uint8_t instance) {
  (void)instance;
  return hid_report_desc;
}

// Singleton pointer so C callbacks can reach the instance.
static USBComm* g_usbcomm = nullptr;

// Called by TinyUSB when host sends an OUT report (HID SET_REPORT).
extern "C" void tud_hid_set_report_cb(
    uint8_t instance,
    uint8_t report_id,
    hid_report_type_t report_type,
    uint8_t const* buffer,
    uint16_t bufsize)
{
  (void)instance;
  (void)report_id;
  (void)report_type;

  if (!g_usbcomm) return;
  if (bufsize != USB_FRAME_SIZE) return;

  memcpy((void*)g_usbcomm->_rx_buf, buffer, USB_FRAME_SIZE);
  g_usbcomm->_rx_new = true;
  g_usbcomm->_rx_count++;
}

// Optional: host can request an IN report via GET_REPORT.
// We’ll just return current tx_buf.
extern "C" uint16_t tud_hid_get_report_cb(
    uint8_t instance,
    uint8_t report_id,
    hid_report_type_t report_type,
    uint8_t* buffer,
    uint16_t reqlen)
{
  (void)instance;
  (void)report_id;
  (void)report_type;

  if (!g_usbcomm) return 0;
  if (reqlen < USB_FRAME_SIZE) return 0;

  memcpy(buffer, (const void*)g_usbcomm->_tx_buf, USB_FRAME_SIZE);
  return USB_FRAME_SIZE;
}

// ------------------------ Class implementation ------------------------

USBComm::USBComm()
: _rx_new(false),
  _connected(false),
  _rx_count(0),
  _tx_count(0),
  _tx_period_ms(0),
  _last_tx_ms(0)
{
  if (!g_usbcomm) g_usbcomm = this;
}

void USBComm::begin() {
  // Nothing required; Arduino core typically calls tusb_init().
  // But calling tud_init() manually can conflict with core, so we don't.
  _rx_new = false;
  _connected = false;
  _rx_count = 0;
  _tx_count = 0;
  _last_tx_ms = millis();
}

void USBComm::update() {
  // Service TinyUSB device tasks (safe to call; helps when core doesn't pump fast enough).
  tud_task();

  _connected = tud_ready();

  if (!_connected) return;

  // Best-effort periodic TX (Device -> Host)
  uint32_t now = millis();
  if (_tx_period_ms > 0) {
    if ((uint32_t)(now - _last_tx_ms) < _tx_period_ms) return;
    _last_tx_ms += _tx_period_ms;
  }

  if (tud_hid_ready()) {
    // report_id = 0 because we used no report IDs.
    bool ok = tud_hid_report(0, _tx_buf, USB_FRAME_SIZE);
    if (ok) _tx_count++;
  }
}
