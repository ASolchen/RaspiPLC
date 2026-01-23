#include "pide.h"
#include <string.h>
#include <Arduino.h>

// ---------------- CONSTRUCTOR ----------------
PIDE::PIDE()
{
    stat.Kp    = 3.0f;
    stat.Ki    = 0.05f;
    stat.Kd    = 0.0f;
    stat.PvMin = 0.0f;
    stat.PvMax = 500.0f;
    stat.Cv    = 0.0f;
    stat.Sp    = 0.0f;
    stat.Pv    = 0.0f;
    stat.Err   = 0.0f;
    stat.Mode  = PID_OFF;
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

    case PID_CMD_READ_STATUS:
        if (out_max < sizeof(pide_stat_t))
            return PID_CMD_ERROR;

        memcpy(out_buf, &stat, sizeof(pide_stat_t));
        *out_len = sizeof(pide_stat_t);
        return PID_CMD_OK;

    case PID_CMD_SET_SP:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.Sp = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_CV:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.Cv = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KP:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.Kp = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KI:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.Ki = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_KD:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.Kd = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_PVMIN:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.PvMin = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_PVMAX:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        stat.PvMax = *(float*)cmd.payload;
        return PID_CMD_OK;

    case PID_CMD_SET_MODE:
        if (cmd.payload_len != sizeof(uint8_t))
            return PID_CMD_ERROR;
        stat.Mode = cmd.payload[0];
        return PID_CMD_OK;

    default:
        return PID_CMD_ERROR;
    }
}

// ---------------- CONTROL LOOP ----------------
float PIDE::update(float pv)
{
    stat.Pv = pv;

    if (stat.Mode == PID_OFF) {
        stat.Cv = 0.0f;
        stat.Sp = stat.Pv;
        return stat.Cv;
    }

    if (stat.Mode == PID_MAN) {
        stat.Sp = stat.Pv;
        return stat.Cv;
    }

    uint32_t now = millis();
    if (last_ms_ == 0) {
        last_ms_ = now;
        return stat.Cv;
    }

    float dt = (now - last_ms_) * 0.001f;
    last_ms_ = now;
    if (dt <= 0.0f)
        return stat.Cv;

    float pv_s = scalePV(stat.Pv);
    float sp_s = scalePV(stat.Sp);

    stat.Err = sp_s - pv_s;

    float dCv =
        stat.Kp * (stat.Err - Err_1)
      + stat.Ki * dt * stat.Err
      + stat.Kd / dt * (stat.Err - 2.0f * Err_1 + Err_2);

    stat.Cv += dCv;
    stat.Cv = clamp(stat.Cv, 0.0f, 100.0f);

    Err_2 = Err_1;
    Err_1 = stat.Err;

    return stat.Cv;
}

// ---------------- HELPERS ----------------
float PIDE::scalePV(float pv) const
{
    if (stat.PvMax <= stat.PvMin)
        return pv;

    float s = (pv - stat.PvMin) * 100.0f /
              (stat.PvMax - stat.PvMin);

    return clamp(s, 0.0f, 100.0f);
}

float PIDE::clamp(float v, float lo, float hi) const
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
