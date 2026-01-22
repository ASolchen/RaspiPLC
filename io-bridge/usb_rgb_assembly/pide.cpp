#include "pide.h"
#include <string.h>
#include <Arduino.h>

// ---------------- CONSTRUCTOR ----------------
PIDE::PIDE(pide_stat_t* stat, pide_ctrl_t* ctrl)
: stat_(stat), ctrl_(ctrl)
{
    if (!isfinite(stat_->Kp)) stat_->Kp = 1.0f;
    if (!isfinite(stat_->Ki)) stat_->Ki = 0.0f;
    if (!isfinite(stat_->Kd)) stat_->Kd = 0.0f;

    if (stat_->PvMin >= stat_->PvMax) {
        stat_->PvMin = 0.0f;
        stat_->PvMax = 100.0f;
    }

    stat_->Cv = 0.0f;
    stat_->Mode = PID_OFF;
}

// ---------------- COMMAND HANDLER ----------------
pid_cmd_result_t PIDE::handle_cmd(
    const pid_cmd_view_t& cmd,
    uint8_t* out_buf,
    uint16_t out_max,
    uint16_t* out_len
){
    *out_len = 0;

    switch (cmd.cmd_id) {

    // ---- READ FULL STATUS ----
    case PID_CMD_READ_STATUS:
        if (out_max < sizeof(pide_stat_t))
            return PID_CMD_ERROR;

        memcpy(out_buf, stat_, sizeof(pide_stat_t));
        *out_len = sizeof(pide_stat_t);
        return PID_CMD_OK;

    // ---- WRITE COMMANDS ----
    case PID_CMD_SET_SP:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->Sp = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_CV:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->Cv = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KP:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->Kp = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KI:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->Ki = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KD:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->Kd = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_PVMIN:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->PvMin = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_PVMAX:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat_->PvMax = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_MODE:
        if (cmd.payload_len != sizeof(uint8_t))
            return PID_CMD_ERROR;
        stat_->Mode = cmd.payload[0];
        return PID_CMD_OK;

    default:
        return PID_CMD_ERROR;
    }
}

// ---------------- CONTROL LOOP ----------------
float PIDE::update(float pv)
{
    stat_->Pv = pv;

    if (stat_->Mode == PID_OFF) {
        stat_->Cv = 0.0f;
        stat_->Sp = stat_->Pv;
        return stat_->Cv;
    }

    if (stat_->Mode == PID_MAN) {
        stat_->Sp = stat_->Pv;
        return stat_->Cv;
    }

    uint32_t now = millis();
    if (last_ms_ == 0) {
        last_ms_ = now;
        return stat_->Cv;
    }

    float dt = (now - last_ms_) * 0.001f;
    last_ms_ = now;
    if (dt <= 0.0f)
        return stat_->Cv;

    float pv_s = scalePV(stat_->Pv);
    float sp_s = scalePV(stat_->Sp);

    stat_->Err = sp_s - pv_s;

    float dCv =
        stat_->Kp * (stat_->Err - Err_1)
      + stat_->Ki * dt * stat_->Err
      + stat_->Kd / dt * (stat_->Err - 2.0f * Err_1 + Err_2);

    stat_->Cv += dCv;
    stat_->Cv = clamp(stat_->Cv, 0.0f, 100.0f);

    Err_2 = Err_1;
    Err_1 = stat_->Err;

    return stat_->Cv;
}

// ---------------- HELPERS ----------------
float PIDE::scalePV(float pv) const
{
    if (stat_->PvMax <= stat_->PvMin)
        return pv;

    float s = (pv - stat_->PvMin) * 100.0f /
              (stat_->PvMax - stat_->PvMin);

    return clamp(s, 0.0f, 100.0f);
}

float PIDE::clamp(float v, float lo, float hi) const
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
