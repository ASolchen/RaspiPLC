import serial
import time
import ctypes
import struct

PORT = "/dev/ttyACM1"     # or /dev/nano_esp32 if using udev symlink
BAUD = 1500000             # cosmetic for USB CDC
FRAME_SIZE = 256
MAGIC = 0xDEADBEEF

# ---------------- ctypes assemblies ----------------

class OutAssembly(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic",        ctypes.c_uint32),
        ("watchdog_out", ctypes.c_uint8),
        ("command_bits", ctypes.c_uint32),
        ("setpoint",     ctypes.c_float),
    ]


class InAssembly(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic",        ctypes.c_uint32),
        ("watchdog_in",  ctypes.c_uint8),
        ("temp1",        ctypes.c_float),
        ("temp2",        ctypes.c_float),
        ("heater1",      ctypes.c_float),
        ("heater2",      ctypes.c_float),
    ]
# ---------------- serial setup ----------------

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=1,
    write_timeout=1
)

print(f"Connected to {PORT}")
time.sleep(0.5)

ser.reset_input_buffer()
ser.reset_output_buffer()

# ---------------- buffers ----------------

out_frame = bytearray(FRAME_SIZE)
in_frame  = bytearray(FRAME_SIZE)

outAsm = OutAssembly.from_buffer(out_frame)
inAsm  = InAssembly.from_buffer(in_frame)


print("Polling Nano ESP32...\n")

while True:
    # ---------- populate OUT assembly ----------
    outAsm.magic = MAGIC
    outAsm.watchdog_out = (inAsm.watchdog_in + 1) & 0xFF
    ser.write(out_frame)
    ser.flush()
    n = ser.readinto(in_frame)
    if (n != FRAME_SIZE) or (inAsm.magic != MAGIC):
        print("Short read / out of sync")
        ser.reset_input_buffer()
        continue


    print(
        f"wd_in={inAsm.watchdog_in:3d} | "
        f"temp1={inAsm.temp1:7.2f} | "
        f"temp2={inAsm.temp2:7.2f}"
    )


    time.sleep(0.005)
