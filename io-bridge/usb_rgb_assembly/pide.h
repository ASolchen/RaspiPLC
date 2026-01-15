#pragma once
#include <stdint.h>

typedef enum {
    PID_NOP  = -1, //no-op value
    PID_OFF  = 0,
    PID_MAN  = 1,
    PID_AUTO = 2
} pide_mode_t;

typedef struct {
    float set_Sp; //set all of these on the other end (Python)
    float set_Cv;
    float set_Kd;
    float set_Kp;
    float set_Ki;
    float set_PvMin;
    float set_PvMax;
    uint8_t set_Mode;
} pide_ctrl_t;

typedef struct {
    /* ---- Runtime / operator-facing ---- */
    float Sp;
    float Pv;
    float Cv;
    uint8_t Mode;
    /* ---- Tuning / config ---- */
    float Kp;
    float Ki;
    float Kd;
    float PvMin;
    float PvMax;
    float Err;
} pide_stat_t;

class PIDE {
public:
    // Constructor
    PIDE(pide_stat_t* stat, pide_ctrl_t* ctrl);

    // Configuration and Control
    void handleCmds();

    // Main call: pass PV, get CV
    float update(float pv);

private:
    pide_stat_t *stat;
    pide_ctrl_t *ctrl;

    // Velocity-form history
    float Err_1;
    float Err_2;

    // Timing
    uint32_t last_ms;

    // Helpers
    float scalePV(float pv) const;
    float clamp(float v, float lo, float hi) const;
};
