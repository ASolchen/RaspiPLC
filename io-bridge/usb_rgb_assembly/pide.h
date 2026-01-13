#pragma once

#include <stdint.h>

class PIDE {
public:
    // Constructor
    PIDE(
        float Kp,
        float Ki,
        float Kd,
        float PvMin = 0.0f,
        float PvMax = 100.0f
    );

    // Configuration
    void setTunings(float Kp, float Ki, float Kd);
    void setSp(float sp);

    // Main call: pass PV, get CV
    float update(float pv);

    // Accessors
    float getCV() const { return Cv; }
    float getError() const { return Err; }

    // Reset controller state (manual CV)
    void reset(float cv = 0.0f);

private:
    // Tunings
    float Kp;
    float Ki;
    float Kd;

    // Scaling
    float PvMin;
    float PvMax;

    // State
    float Sp;
    float Pv;
    float Err;
    float Cv;

    // Velocity-form history
    float Err_1;
    float Err_2;

    // Timing
    uint32_t last_ms;

    // Helpers
    float scalePV(float pv) const;
    float clamp(float v, float lo, float hi) const;
};
