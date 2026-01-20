#pragma once
#include <stdint.h>


#define BIT(n) (1UL << (n))
typedef enum {
    SET_SP_BIT = 0,
    SET_CV_BIT = 1,
    SET_KP_BIT = 2,
    SET_KI_BIT = 3,
    SET_KD_BIT = 4,
    SET_PVMIN_BIT = 5,
    SET_PVMAX_BIT = 6,
    SET_MODE_BIT = 7,
} pide_set_bit_t;
#define SET_SP_MASK     BIT(SET_SP_BIT)
#define SET_CV_MASK     BIT(SET_CV_BIT)
#define SET_KP_MASK     BIT(SET_KP_BIT)
#define SET_KI_MASK     BIT(SET_KI_BIT)
#define SET_KD_MASK     BIT(SET_KD_BIT)
#define SET_PVMIN_MASK  BIT(SET_PVMIN_BIT)
#define SET_PVMAX_MASK  BIT(SET_PVMAX_BIT)
#define SET_MODE_MASK   BIT(SET_MODE_BIT)
#define SET_REQUEST(ctrl, mask)    ((ctrl)->setBits |= (mask))
#define CLEAR_REQUEST(ctrl, mask)  ((ctrl)->setBits &= ~(mask))
#define HAS_REQUEST(ctrl, mask)    (((ctrl)->setBits & (mask)) != 0)

typedef enum {
    PID_NOP  = -1, //no-op value
    PID_OFF  = 0,
    PID_MAN  = 1,
    PID_AUTO = 2
} pide_mode_t;



typedef struct {
    uint32_t setBits;
    float set_Sp; //set all of these on the other end (Python) 
    float set_Cv;
    float set_Kp;
    float set_Ki;
    float set_Kd;
    float set_PvMin;
    float set_PvMax;
    uint8_t set_Mode;
    uint8_t _pad65;
    uint8_t _pad66;
    uint8_t _pad67;
} pide_ctrl_t;

typedef struct {
    /* ---- Runtime / operator-facing ---- */
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
    uint8_t _pad37;
    uint8_t _pad38;
    uint8_t _pad39;

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
