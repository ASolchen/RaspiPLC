#include "max6675.h"

MAX6675::MAX6675(uint8_t sck, uint8_t cs, uint8_t miso)
: _cs(cs)
{
    pinMode(_cs, OUTPUT);
    digitalWrite(_cs, HIGH);

    // Use hardware SPI pins supplied by core
    SPI.begin(sck, miso, -1, cs);
}

float MAX6675::read() {
    uint16_t v = 0;

    // MAX6675 max SPI clock is 4.3 MHz
    SPI.beginTransaction(SPISettings(100000, MSBFIRST, SPI_MODE0));

    digitalWrite(_cs, LOW);
    delayMicroseconds(1);

    v = SPI.transfer16(0x0000);

    digitalWrite(_cs, HIGH);
    SPI.endTransaction();
    delayMicroseconds(1);

    // Fault bit (D2)
    if (v & 0x4) {
        return NAN;
    }

    // Bits 14..3 are temperature
    v >>= 3;

    return v * 0.25f;
}

float MAX6675::readF() {
    float c = read();
    if (isnan(c)) {
        return NAN;
    }
    return c * 9.0f / 5.0f + 32.0f;
}
