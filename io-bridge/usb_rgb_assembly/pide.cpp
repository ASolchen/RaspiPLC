#include "pide.h"
#include <Arduino.h>

PIDE::PIDE(
    float Kp_,
    float Ki_,
    float Kd_,
    float PvMin_,
    float PvMax_
)
: Kp(Kp_),
  Ki(Ki_),
  Kd(Kd_),
  PvMin(PvMin_),
  PvMax(PvMax_),
  Sp(0.0f),
  Pv(0.0f),
  Err(0.0f),
  Cv(0.0f),
  Err_1(0.0f),
  Err_2(0.0f),
  last_ms(0)
{
}

void PIDE::setTunings(float Kp_, float Ki_, float Kd_) {
    Kp = Kp_;
    Ki = Ki_;
    Kd = Kd_;
}

void PIDE::setSp(float sp) {
    Sp = sp;
}

float PIDE::update(float pv) {
    Pv = pv;
    uint32_t now = millis();

    // First call: initialize timing
    if (last_ms == 0) {
        last_ms = now;
        return Cv;
    }

    float dt = (now - last_ms) * 0.001f;  // ms → seconds
    last_ms = now;

    if (dt <= 0.0f) {
        return Cv;
    }

    // ---- Scale PV & SP to 0–100% ----
    float pv_s = scalePV(Pv);
    float sp_s = scalePV(Sp);

    // ---- Error ----
    Err = sp_s - pv_s;

    // ---- Velocity PID ----
    float dCv =
        Kp * (Err - Err_1)
      + Ki * dt * Err
      + Kd / dt * (Err - 2.0f * Err_1 + Err_2);

    Cv += dCv;

    // ---- Clamp output ----
    Cv = clamp(Cv, 0.0f, 100.0f);

    // ---- Shift history ----
    Err_2 = Err_1;
    Err_1 = Err;

    return Cv;
}

void PIDE::reset(float cv) {
    Cv = clamp(cv, 0.0f, 100.0f);
    Err = 0.0f;
    Err_1 = 0.0f;
    Err_2 = 0.0f;
    Sp = Pv; //bumpless
}

float PIDE::scalePV(float pv) const {
    if (PvMax <= PvMin) {
        return pv;
    }

    float s = (pv - PvMin) * 100.0f / (PvMax - PvMin);
    return clamp(s, 0.0f, 100.0f);
}

float PIDE::clamp(float v, float lo, float hi) const {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
