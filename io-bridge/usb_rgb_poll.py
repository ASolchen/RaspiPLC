import serial
import time
import ctypes

# ---------------- configuration ----------------
PORT = "COM8"              # or /dev/ttyACM0, /dev/nano_esp32
BAUD = 500000              # cosmetic for USB CDC
FRAME_SIZE = 256
MAGIC = 0xDEADBEEF

# ---------------- ctypes structures ----------------

class UsbCommCmdBits(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("raw", ctypes.c_uint32),
    ]


class PideStat(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("Sp",    ctypes.c_float),
        ("Pv",    ctypes.c_float),
        ("Cv",    ctypes.c_float),
        ("Kp",    ctypes.c_float),
        ("Ki",    ctypes.c_float),
        ("Kd",    ctypes.c_float),
        ("PvMin", ctypes.c_float),
        ("PvMax", ctypes.c_float),
        ("Err",   ctypes.c_float),
        ("Mode",  ctypes.c_uint8),
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


class PideCtrl(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("setBits",    ctypes.c_uint32),
        ("set_Sp",    ctypes.c_float),
        ("set_Cv",    ctypes.c_float),
        ("set_Kd",    ctypes.c_float),
        ("set_Kp",    ctypes.c_float),
        ("set_Ki",    ctypes.c_float),
        ("set_PvMin", ctypes.c_float),
        ("set_PvMax", ctypes.c_float),
        ("set_Mode",  ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * (256 - (4 + 1 + 4) - (7 * 4 + 1))),
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

# destination pointer (persistent)
dst_ptr = ctypes.addressof(ctypes.c_char.from_buffer(in_frame))

# ---------------- serial loop ----------------

print("Polling Nano ESP32...\n")

with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as ser:
    print(f"Connected to {PORT}")
    time.sleep(0.2)

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # initialize outbound control values
    outAsm.htr1_pide_ctrl.set_Sp    = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Cv    = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Kd    = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Kp    = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Ki    = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_PvMin = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_PvMax = NOP_FLOAT_VALUE
    outAsm.htr1_pide_ctrl.set_Mode  = 0xFF

    rx = bytearray()

    for count in range(1000):
        # ---------- populate OUT frame ----------
        outAsm.magic = MAGIC
        outAsm.watchdog_out = inAsm.watchdog_in & 0xFF
        outAsm.command_bits.raw = 0

        ser.write(out_frame)
        ser.flush()

        # ---------- receive / accumulate ----------
        rx += ser.read(128)

        # ---------- sliding frame parser ----------
        while len(rx) >= FRAME_SIZE:
            magic = int.from_bytes(rx[0:4], "little")

            if magic != MAGIC:
                rx.pop(0)
                continue

            frame = rx[:FRAME_SIZE]
            rx = rx[FRAME_SIZE:]

            # ---- correct memmove (dst + src pointers) ----
            src_buf = ctypes.c_char * FRAME_SIZE
            src = src_buf.from_buffer_copy(frame)
            ctypes.memmove(dst_ptr, ctypes.addressof(src), FRAME_SIZE)

            # ---------- consume data ----------
            ps = inAsm.htr1_pide_stat
            print(
                f"{ps.Sp:.2f}, "
                f"{ps.Pv:.2f}, "
                f"{ps.Cv:.2f}, "
                f"{ps.Kp:.2f}, "
                f"{ps.Ki:.2f}, "
                f"{ps.Kd:.2f}"
            )

        time.sleep(0.05)
