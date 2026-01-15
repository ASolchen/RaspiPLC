import serial
import time
import ctypes

PORT = "/dev/ttyACM0"      # or /dev/nano_esp32 if using udev symlink
BAUD = 1500000             # cosmetic for USB CDC
FRAME_SIZE = 256
MAGIC = 0xDEADBEEF

NOP_FLOAT_THRESH = -999.0
NOP_FLOAT_VALUE  = -999.9

# ---------------- ctypes structures ----------------
# Your union is effectively a uint32_t "raw" on the wire.
class UsbCommCmdBits(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("raw", ctypes.c_uint32),
    ]


# usb_comm_in_t layout (packed):
#   uint32 magic        (4)
#   uint8  watchdog_in  (1)
#   uint8  pad5         (1)
#   uint8  pad6         (1)
#   uint8  pad7         (1)
#   float temp1         (4)
#   float temp2         (4)
#   float heater1       (4)
#   float heater2       (4)
#   pide_stat_t         (rest of frame)
#
# So htr1_pide_stat begins at offset:
#   4 + 1 + 3 + 16 = 24
IN_HEADER_SIZE = 24
PIDE_STAT_BYTES = FRAME_SIZE - IN_HEADER_SIZE  # 232 bytes


class PideStat(ctypes.LittleEndianStructure):
    """

    The rest is padded out to the full size of the remaining frame so offsets stay correct.
    """
    _pack_ = 1
    _fields_ = [
        ("Sp",  ctypes.c_float),
        ("Pv",  ctypes.c_float),
        ("Cv",  ctypes.c_float),
        ("Kp", ctypes.c_float),
        ("Ki", ctypes.c_float),
        ("Kd", ctypes.c_float),
        ("PvMin", ctypes.c_float),
        ("PvMax", ctypes.c_float),
        ("Err", ctypes.c_float),
        ("Mode", ctypes.c_uint8),
        ("_pad37", ctypes.c_uint8),
        ("_pad38", ctypes.c_uint8),
        ("_pad39", ctypes.c_uint8),
    ]


class InAssembly(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic",       ctypes.c_uint32),
        ("watchdog_in", ctypes.c_uint8),
        ("pad5",        ctypes.c_uint8),
        ("pad6",        ctypes.c_uint8),
        ("pad7",        ctypes.c_uint8),
        ("temp1",       ctypes.c_float),
        ("temp2",       ctypes.c_float),
        ("heater1",     ctypes.c_float),
        ("heater2",     ctypes.c_float),
        ("htr1_pide_stat", PideStat),
    ]


# usb_comm_out_t layout (packed):
#   uint32 magic        (4)
#   uint8  watchdog_out (1)
#   usb_comm_cmd_bits_t (4)
#   pide_ctrl_t         (rest of frame)
OUT_HEADER_SIZE = 4 + 1 + 4  # 9 bytes
PIDE_CTRL_BYTES = FRAME_SIZE - OUT_HEADER_SIZE  # 247 bytes


class PideCtrl(ctypes.LittleEndianStructure):
    """
    Your provided struct:
      float set_Sp;
      float set_Cv;
      float set_Kd;  
      float set_Kp;
      float set_Ki;
      float set_PvMin;
      float set_PvMax;
      uint8_t set_Mode;

    Pad the remainder so the OUT frame remains 256 bytes.
    """
    _pack_ = 1
    _fields_ = [
        ("set_Sp",   ctypes.c_float),
        ("set_Cv",   ctypes.c_float),
        ("set_Kd",   ctypes.c_float),
        ("set_Kp",   ctypes.c_float),
        ("set_Ki",   ctypes.c_float),
        ("set_PvMin", ctypes.c_float),
        ("set_PvMax", ctypes.c_float),
        ("set_Mode", ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * (PIDE_CTRL_BYTES - (7 * 4 + 1))),  # 247 - 29 = 218
    ]


class OutAssembly(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic",        ctypes.c_uint32),
        ("watchdog_out", ctypes.c_uint8),
        ("command_bits", UsbCommCmdBits),
        ("htr1_pide_ctrl", PideCtrl),
    ]


# ---------------- buffers ----------------
out_frame = bytearray(FRAME_SIZE)
in_frame  = bytearray(FRAME_SIZE)

outAsm = OutAssembly.from_buffer(out_frame)
inAsm  = InAssembly.from_buffer(in_frame)

# ---------------- serial loop ----------------
print("Polling Nano ESP32...\n")

with serial.Serial(PORT, BAUD, timeout=1, write_timeout=1) as ser:
    print(f"Connected to {PORT}")
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)

    # Initialize all "set_" floats to NOP so you don't accidentally apply stale values
    outAsm.htr1_pide_ctrl.set_Sp = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Cv = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Kd = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Kp = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Ki = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_PvMin = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_PvMax = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Mode = -1  # PID_OFF by default

    for count in range(1000000):
        # ---------- populate OUT assembly ----------
        outAsm.magic = MAGIC

        # Echo watchdog back like you were doing
        outAsm.watchdog_out = inAsm.watchdog_in & 0xFF

        # (Optional) command bits
        outAsm.command_bits.raw = 0
        #outAsm.htr1_pide_ctrl.set_Sp = count * 0.01
        # ---------- exchange ----------
        ser.write(out_frame)
        ser.flush()

        n = ser.readinto(in_frame)
        if n != FRAME_SIZE:
            print("Short read")
            continue

        if inAsm.magic != MAGIC:
            print("out of sync")
            ser.reset_input_buffer()
            continue

        # ---------- Arduino-style print ----------
        ps = inAsm.htr1_pide_stat
        #print(f"SP {ps.Sp} PV {ps.Pv} CV {ps.Cv} ERR {ps.Err} HTR1 {inAsm.temp1}")
        print(f"{ps.Sp}, {ps.Pv}, {ps.Cv}, {ps.Kp}, {ps.Ki}, {ps.Kd},")

        time.sleep(0.2)
