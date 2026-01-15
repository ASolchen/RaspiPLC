#include "pide.h"
#include <Arduino.h>
#define NOP_FLOAT_THRESH (-999.0f) //threshold
#define NOP_FLOAT_VALUE    (-999.9f) //no-op value

PIDE::PIDE(pide_stat_t* stat_, pide_ctrl_t* ctrl_)
: stat(stat_), ctrl(ctrl_)
{
    if (!isfinite(stat->Kp)) stat->Kp = 1.0f;
    if (!isfinite(stat->Ki)) stat->Ki = 0.0f;
    if (!isfinite(stat->Kd)) stat->Kd = 0.0f;

    if (stat->PvMin >= stat->PvMax) {
        stat->PvMin = 0.0f;
        stat->PvMax = 100.0f;
    }
    stat->Cv = 0.0f;
    //set PID config (eeprom??)
    ctrl->set_Sp = 100.0;
    ctrl->set_Kp = 2.0;
    ctrl->set_Ki = 0.1;
    ctrl->set_Kd = 0.0;
    ctrl->set_Mode = PID_MAN;
    ctrl->set_Cv = 30.0;
    ctrl->set_PvMin = 0.0;
    ctrl->set_PvMax = 500.0;
}

void PIDE::handleCmds() {
    /* Mode (non-float, no sentinel needed) */
    if (ctrl->set_Mode != PID_NOP) {
        stat->Mode = ctrl->set_Mode;
    }
    /* Setpoint */
    if (ctrl->set_Sp > NOP_FLOAT_THRESH) {
        stat->Sp = ctrl->set_Sp;
        ctrl->set_Sp = NOP_FLOAT_VALUE;
    }
    /* Control Variable (ignored if not manualCV) */
    if (ctrl->set_Cv > NOP_FLOAT_THRESH) {
        if(stat->Mode == PID_MAN ){
            stat->Cv = ctrl->set_Cv;
            clamp(stat->Cv, 0.0f, 100.0f);
        }
        ctrl->set_Cv = NOP_FLOAT_VALUE;
    }

    /* Gains */
    if (ctrl->set_Kp > NOP_FLOAT_THRESH) {
        stat->Kp = ctrl->set_Kp;
        ctrl->set_Kp = NOP_FLOAT_VALUE;
    }

    if (ctrl->set_Ki > NOP_FLOAT_THRESH) {
        stat->Ki = ctrl->set_Ki;
        ctrl->set_Ki = NOP_FLOAT_VALUE;
    }

    if (ctrl->set_Kd > NOP_FLOAT_THRESH) {
        stat->Kd = ctrl->set_Kd;
        ctrl->set_Kd = NOP_FLOAT_VALUE;
    }

    /* Limits */
    if (ctrl->set_PvMin > NOP_FLOAT_THRESH) {
        stat->PvMin = ctrl->set_PvMin;
        ctrl->set_PvMin = NOP_FLOAT_VALUE;
    }

    if (ctrl->set_PvMax > NOP_FLOAT_THRESH) {
        stat->PvMax = ctrl->set_PvMax;
        ctrl->set_PvMax = NOP_FLOAT_VALUE;
    }
}


float PIDE::update(float pv) {
    handleCmds();
    if (stat->Mode == PID_OFF){ //cv zero and sp tracking
        stat->Cv = 0.0;
        stat->Pv = pv;
        stat->Sp = stat->Pv;
        return stat->Cv;
    }
    if (stat->Mode == PID_MAN){ //cv manually set by ctrl->set_Cv and sp tracking
        stat->Sp = stat->Pv;
        return stat->Cv;
    }
    if (stat->Mode != PID_AUTO){ //someone did something stupid
        stat->Cv = 0.0;
        stat->Mode = PID_OFF;
        return stat->Cv;
    }
    stat->Pv = pv;
    uint32_t now = millis();

    // First call: initialize timing
    if (last_ms == 0) {
        last_ms = now;
        return stat->Cv;
    }

    float dt = (now - last_ms) * 0.001f;  // ms → seconds
    last_ms = now;

    if (dt <= 0.0f) {
        return stat->Cv;
    }

    // ---- Scale PV & SP to 0–100% ----
    float pv_s = scalePV(stat->Pv);
    float sp_s = scalePV(stat->Sp);

    // ---- Error ----
    stat->Err = sp_s - pv_s;

    // ---- Velocity PID ----
    float dCv =
        stat->Kp * (stat->Err - Err_1)
      + stat->Ki * dt * stat->Err
      + stat->Kd / dt * (stat->Err - 2.0f * Err_1 + Err_2);

    stat->Cv += dCv;

    // ---- Clamp output ----
    stat->Cv = clamp(stat->Cv, 0.0f, 100.0f);

    // ---- Shift history ----
    Err_2 = Err_1;
    Err_1 = stat->Err;

    return stat->Cv;
}

float PIDE::scalePV(float pv) const {
    if (stat->PvMax <= stat->PvMin) {
        return pv;
    }

    float s = (pv - stat->PvMin) * 100.0f / (stat->PvMax - stat->PvMin);
    return clamp(s, 0.0f, 100.0f);
}

float PIDE::clamp(float v, float lo, float hi) const {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
