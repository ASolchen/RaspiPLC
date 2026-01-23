// temp_ctrl.cpp
#include "temp_ctrl.h"
#include <string.h>

// ---------------- CONSTRUCTOR ----------------
TempCtrl::TempCtrl()
{
    Mode     = TC_OFF;
    CtrlMode = TC_CTRL_OFF;

    pid.stat.Mode = PID_OFF;
}

// ---------------- COMMAND HANDLER ----------------
pid_cmd_result_t TempCtrl::handle_cmd(
    const pid_cmd_view_t& cmd,
    uint8_t* out_buf,
    uint16_t out_max,
    uint16_t* out_len
){
    *out_len = 0;

    switch (cmd.cmd_id) {

    // ---------- READ FULL STATUS ----------
    case TC_CMD_READ_STATUS: {
        if (out_max < sizeof(tempctrl_stat_t))
            return PID_CMD_ERROR;

        tempctrl_stat_t st;
        st.Mode     = (uint8_t)Mode;
        st.CtrlMode = (uint8_t)CtrlMode;
        st._pad1    = 0;
        st._pad2    = 0;
        st.Sp = Sp;
        memcpy(&st.pid, &pid.stat, sizeof(pide_stat_t));

        memcpy(out_buf, &st, sizeof(st));
        *out_len = sizeof(st);
        return PID_CMD_OK;
    }

    // ---------- TEMP CTRL COMMANDS ----------
    case TC_CMD_SET_MODE:
        if (cmd.payload_len != sizeof(uint8_t))
            return PID_CMD_ERROR;
        Mode = (tempctrl_mode_t)cmd.payload[0];
        return PID_CMD_OK;

    case TC_CMD_SET_SP:
        if (cmd.payload_len != sizeof(float))
            return PID_CMD_ERROR;
        Sp = *(float*)cmd.payload;
        return PID_CMD_OK;

    case TC_CMD_SET_CTRL:
        if (cmd.payload_len != sizeof(uint8_t))
            return PID_CMD_ERROR;
        CtrlMode = (tempctrl_ctrlmode_t)cmd.payload[0];
        return PID_CMD_OK;

    // ---------- FALL THROUGH TO PIDE ----------
    default:
        return pid.handle_cmd(cmd, out_buf, out_max, out_len);
    }
}

// ---------------- UPDATE ----------------
float TempCtrl::update(float pv)
{
    float err = Sp - pv;

    switch (Mode) {

    case TC_OFF:
        CtrlMode = TC_CTRL_OFF;
        pid.stat.Mode = PID_OFF;
        pid.stat.Cv = 0.0f;
        pid.stat.Sp = pv;
        return pid.update(pv);

    case TC_OPER_MANUAL:
        CtrlMode = TC_CTRL_OFF;
        pid.stat.Mode = PID_MAN;
        pid.stat.Sp = pv;
        return pid.update(pv);

    case TC_OPER_AUTO:
        CtrlMode = TC_CTRL_CLOSED_LOOP;
        pid.stat.Mode = PID_AUTO;
        pid.stat.Sp = Sp;
        return pid.update(pv);

    case TC_PGM_AUTO:
        updateCtrlMode(err);

        switch (CtrlMode) {

          case TC_CTRL_OFF:
              pid.stat.Mode = PID_OFF;
              pid.stat.Cv   = 0.0f;
              pid.stat.Sp   = pv;   // track PV
              break;

          case TC_CTRL_BOOST:
              pid.stat.Mode = PID_MAN;
              pid.stat.Cv   = BoostCv;
              pid.stat.Sp   = pv;
              break;

          case TC_CTRL_FEEDFWD:
              pid.stat.Mode = PID_MAN;
              pid.stat.Cv   = FeedFwdCv;
              pid.stat.Sp   = pv;
              break;

          case TC_CTRL_CLOSED_LOOP:
              pid.stat.Mode = PID_AUTO;
              pid.stat.Sp   = Sp;
              break;
          }

        return pid.update(pv);
    }

    return pid.stat.Cv;
}

// ---------------- STATE MACHINE ----------------
void TempCtrl::updateCtrlMode(float err)
{
    // Large negative error → force OFF (too hot)
    if (err <= -Deadband) {
        CtrlMode = TC_CTRL_OFF;
        return;
    }

    // Large positive error → BOOST
    if (err >= BoostErrThresh) {
        CtrlMode = TC_CTRL_BOOST;
        return;
    }

    // Inside deadband → CLOSED LOOP
    if (fabsf(err) <= Deadband) {
        CtrlMode = TC_CTRL_CLOSED_LOOP;
        return;
    }

    // Otherwise → FEED FORWARD region
    CtrlMode = TC_CTRL_FEEDFWD;
}
