#pragma once

#include <stdint.h>
#include <stddef.h>

// ---------------- PID MODES ----------------
typedef enum {
    PID_OFF  = 0,
    PID_MAN  = 1,
    PID_AUTO = 2
} pide_mode_t;

// ---------------- COMMAND IDS (PID-SPECIFIC) ----------------
typedef enum {
    PID_CMD_READ_STATUS = 0x01,

    PID_CMD_SET_SP      = 0x10,
    PID_CMD_SET_CV      = 0x11,
    PID_CMD_SET_KP      = 0x12,
    PID_CMD_SET_KI      = 0x13,
    PID_CMD_SET_KD      = 0x14,
    PID_CMD_SET_PVMIN   = 0x15,
    PID_CMD_SET_PVMAX   = 0x16,
    PID_CMD_SET_MODE    = 0x17
} pid_cmd_id_t;

// ---------------- STATUS STRUCT ----------------
typedef struct __attribute__((packed)) {
    float Sp;
    float Pv;
    float Cv;
    float Kp;
    float Ki;
    float Kd;
    float PvMin;
    float PvMax;
    float Err;
    uint8_t Mode;
    uint8_t _pad1;
    uint8_t _pad2;
    uint8_t _pad3;
} pide_stat_t;

// ---------------- CONTROL STRUCT ----------------
typedef struct {
    float set_Sp;
    float set_Cv;
    float set_Kp;
    float set_Ki;
    float set_Kd;
    float set_PvMin;
    float set_PvMax;
    uint8_t set_Mode;
} pide_ctrl_t;

// ---------------- COMMAND VIEW (GENERIC) ----------------
typedef struct {
    uint8_t  cmd_id;
    const uint8_t* payload;
    uint16_t payload_len;
} pid_cmd_view_t;

// ---------------- HANDLER RESULT ----------------
typedef enum {
    PID_CMD_OK = 0,
    PID_CMD_ERROR = 1
} pid_cmd_result_t;

// ---------------- PIDE CLASS ----------------
class PIDE {
public:
    PIDE(pide_stat_t* stat, pide_ctrl_t* ctrl);

    // Called by control loop
    float update(float pv);

    // Generic command handler (USB-agnostic)
    pid_cmd_result_t handle_cmd(
        const pid_cmd_view_t& cmd,
        uint8_t* out_buf,
        uint16_t out_max,
        uint16_t* out_len
    );

private:
    pide_stat_t* stat_;
    pide_ctrl_t* ctrl_;

    float Err_1 = 0.0f;
    float Err_2 = 0.0f;
    uint32_t last_ms_ = 0;

    float scalePV(float pv) const;
    float clamp(float v, float lo, float hi) const;
};
