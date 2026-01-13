#pragma once

#include <Arduino.h>
#include <SPI.h>

class MAX6675 {
public:
    // Constructor
    MAX6675(uint8_t sck, uint8_t cs, uint8_t miso);

    // Read temperature
    float read();   // Celsius
    float readF();  // Fahrenheit

private:
    uint8_t _cs;
};
