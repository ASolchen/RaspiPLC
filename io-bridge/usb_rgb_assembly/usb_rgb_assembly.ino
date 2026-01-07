#include <Arduino.h>
#include "tusb.h"
#include <Adafruit_NeoPixel.h>

/* ---------------- RGB ---------------- */

#define RGB_PIN   21
#define RGB_COUNT 1

Adafruit_NeoPixel rgb(RGB_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);

/* ---------------- USB Buffers ---------------- */

static uint8_t usb_out[256];
static uint8_t usb_in[256];

#pragma pack(push, 1)
struct OutputAssembly {
    uint8_t  enable;
    uint8_t  r;
    uint8_t  g;
    uint8_t  b;
    uint32_t counter;
};

struct InputAssembly {
    uint8_t  status;
    uint8_t  pad[3];
    uint32_t echo;
};
#pragma pack(pop)

OutputAssembly *outAsm = (OutputAssembly *)usb_out;
InputAssembly  *inAsm  = (InputAssembly  *)usb_in;

/* ---------------- Setup ---------------- */

void setup() {
    rgb.begin();
    rgb.clear();
    rgb.show();

    memset(usb_out, 0, sizeof(usb_out));
    memset(usb_in,  0, sizeof(usb_in));
}

/* ---------------- Main Loop ---------------- */

void loop() {
    tud_task();  // TinyUSB background processing

    // OUT assembly available?
    if (tud_vendor_available() >= sizeof(usb_out)) {
        tud_vendor_read(usb_out, sizeof(usb_out));

        if (outAsm->enable) {
            rgb.setPixelColor(
                0,
                rgb.Color(outAsm->r, outAsm->g, outAsm->b)
            );
        } else {
            rgb.setPixelColor(0, 0);
        }

        rgb.show();

        inAsm->status = 0;
        inAsm->echo   = outAsm->counter;
    }

    // IN endpoint has room?
    if (tud_vendor_write_available() >= sizeof(usb_in)) {
        tud_vendor_write(usb_in, sizeof(usb_in));
        tud_vendor_flush();
    }
}

