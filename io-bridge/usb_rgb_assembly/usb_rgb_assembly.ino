#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

#define FRAME_SIZE 256
#define RGB_PIN 18
#define RGB_COUNT 1

typedef struct __attribute__((packed)) {
  uint8_t  enable;
  uint8_t  r;
  uint8_t  g;
  uint8_t  b;
  uint32_t counter;
} out_assembly_t;

typedef struct __attribute__((packed)) {
  uint8_t  status;
  uint8_t  _pad[3];
  uint32_t echo;
} in_assembly_t;

uint8_t rx_buf[FRAME_SIZE];
uint8_t tx_buf[FRAME_SIZE];

out_assembly_t *outAsm = (out_assembly_t *)rx_buf;
in_assembly_t  *inAsm  = (in_assembly_t  *)tx_buf;

Adafruit_NeoPixel rgb(RGB_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  rgb.begin();
  rgb.clear();
  rgb.show();

  memset(rx_buf, 0, sizeof(rx_buf));
  memset(tx_buf, 0, sizeof(tx_buf));
}

void loop() {
  if (Serial.available() >= FRAME_SIZE) {
    Serial.readBytes(rx_buf, FRAME_SIZE);

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

    Serial.write(tx_buf, FRAME_SIZE);
  }
}
