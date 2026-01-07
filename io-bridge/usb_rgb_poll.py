import serial
import struct
import time

PORT = "/dev/ttyACM0"   # adjust if needed
BAUD = 115200
FRAME_SIZE = 256

OUT_FMT = "<BBBBI"
IN_FMT  = "<B3xI"

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=1,
    write_timeout=1
)

counter = 0
colors = [(255,0,0), (0,255,0), (0,0,255)]
idx = 0

print("Connected to Nano ESP32 CDC")

while True:
    r,g,b = colors[idx]

    out_buf = bytearray(FRAME_SIZE)
    struct.pack_into(OUT_FMT, out_buf, 0, 1, r, g, b, counter)

    ser.write(out_buf)
    ser.flush()

    in_buf = ser.read(FRAME_SIZE)
    if len(in_buf) != FRAME_SIZE:
        print("Short read")
        continue

    status, echo = struct.unpack_from(IN_FMT, in_buf, 0)
    print(f"status={status} echo={echo}")

    counter += 1
    idx = (idx + 1) % len(colors)
    time.sleep(0.5)
