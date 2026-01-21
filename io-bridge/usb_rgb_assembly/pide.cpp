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
    ctrl->set_Mode = PID_AUTO;
    ctrl->set_Cv = 30.0;
    ctrl->set_PvMin = 0.0;
    ctrl->set_PvMax = 500.0;
}

void PIDE::handleCmds() {
    /* Mode */
    if (HAS_REQUEST(ctrl, SET_MODE_MASK)) {
      if (ctrl->set_Mode <= PID_AUTO) {
          stat->Mode = ctrl->set_Mode;
      }
    CLEAR_REQUEST(ctrl, SET_MODE_MASK);
    }
    /* Setpoint */
    if (HAS_REQUEST(ctrl, SET_SP_MASK)) {
      stat->Sp = ctrl->set_Sp;
    CLEAR_REQUEST(ctrl, SET_SP_MASK);
    }
    /* Control Variable (ignored if not manualCV) */
    if (HAS_REQUEST(ctrl, SET_CV_MASK)) {
      if(stat->Mode == PID_MAN){
        stat->Cv = ctrl->set_Cv;
      }
    CLEAR_REQUEST(ctrl, SET_CV_MASK);
    }

    /* Gains */
    if (HAS_REQUEST(ctrl, SET_KP_MASK)) {
      stat->Kp = ctrl->set_Kp;
    CLEAR_REQUEST(ctrl, SET_KP_MASK);
    }
    if (HAS_REQUEST(ctrl, SET_KI_MASK)) {
      stat->Ki = ctrl->set_Ki;
    CLEAR_REQUEST(ctrl, SET_KI_MASK);
    }
    if (HAS_REQUEST(ctrl, SET_KD_MASK)) {
      stat->Kd = ctrl->set_Kd;
    CLEAR_REQUEST(ctrl, SET_KD_MASK);
    }

    /* Limits */
    if (HAS_REQUEST(ctrl, SET_PVMIN_MASK)) {
      stat->PvMin = ctrl->set_PvMin;
    CLEAR_REQUEST(ctrl, SET_PVMIN_MASK);
    }
    if (HAS_REQUEST(ctrl, SET_PVMAX_MASK)) {
      stat->PvMax = ctrl->set_PvMax;
    CLEAR_REQUEST(ctrl, SET_PVMAX_MASK);
    }
}


float PIDE::update(float pv) {
    stat->Pv = pv; //always update pv
    if (stat->Mode == PID_OFF){ //cv zero and sp tracking
        stat->Cv = 0.0;
        
        stat->Sp = stat->Pv;
        return stat->Cv;
    }
    if (stat->Mode == PID_MAN){ //cv manually set by ctrl->set_Cv and sp tracking
        stat->Sp = stat->Pv;
        return stat->Cv;
    }
    if (stat->Mode != PID_AUTO){ //someone did something stupid
        stat->Cv = 0.0;
        stat->Mode = PID_AUTO;
        return stat->Cv;
    }
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
