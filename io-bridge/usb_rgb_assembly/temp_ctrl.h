// temp_ctrl.h
#pragma once

#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include "pide.h"

// ---------------- TEMP CTRL MODES ----------------
typedef enum {
    TC_OFF = 0,
    TC_OPER_MANUAL,
    TC_OPER_AUTO,
    TC_PGM_AUTO
} tempctrl_mode_t;

// ---------------- CONTROL STATE MACHINE ----------------
typedef enum {
    TC_CTRL_OFF = 0,
    TC_CTRL_BOOST,
    TC_CTRL_FEEDFWD,
    TC_CTRL_CLOSED_LOOP
} tempctrl_ctrlmode_t;

// ---------------- COMMAND IDS ----------------
typedef enum {
    TC_CMD_READ_STATUS = 0x01,

    TC_CMD_SET_MODE    = 0x20,
    TC_CMD_SET_SP      = 0x21,
    TC_CMD_SET_CTRL    = 0x22   // optional override / debug
} tempctrl_cmd_id_t;

// ---------------- STATUS STRUCT ----------------
// Returned by READ_STATUS
typedef struct __attribute__((packed)) {
    uint8_t Mode;
    uint8_t CtrlMode;
    uint8_t _pad1;
    uint8_t _pad2;
    float Sp;
    pide_stat_t pid;
} tempctrl_stat_t;

// ---------------- TEMP CTRL CLASS ----------------
class TempCtrl {
public:
    TempCtrl();

    // Embedded PID
    PIDE pid;

    // Operator-facing setpoint
    float Sp;



    // Modes
    tempctrl_mode_t Mode;
    tempctrl_ctrlmode_t CtrlMode = TC_CTRL_OFF;

    // Behavior parameters
    float Deadband        = 150.0f;   // deg around SP
    float BoostErrThresh  = 160.0f;  // deg
    float BoostCv         = 100.0f; // %
    float FeedFwdCv       = 10.0f;  // %

    // Control update
    float update(float pv);

    // Command handler (USB-agnostic)
    pid_cmd_result_t handle_cmd(
        const pid_cmd_view_t& cmd,
        uint8_t* out_buf,
        uint16_t out_max,
        uint16_t* out_len
    );

private:
    void updateCtrlMode(float err);
};
