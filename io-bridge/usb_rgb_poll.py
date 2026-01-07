import usb1
import struct
import time

VID = 0x2341
PID = 0x0070

INTERFACE_NUM = 1   # Vendor interface (MI_01)

OUT_SIZE = 256
IN_SIZE  = 256

OUT_FMT = "<BBBBI"   # enable, r, g, b, counter
IN_FMT  = "<B3xI"    # status, pad, echo

ctx = usb1.USBContext()
handle = None
device = None

# Find device
for dev in ctx.getDeviceList():
    if dev.getVendorID() == VID and dev.getProductID() == PID:
        device = dev
        handle = dev.open()
        break

if handle is None:
    raise RuntimeError("Nano ESP32 not found")

handle.claimInterface(INTERFACE_NUM)

# Discover endpoints
EP_OUT = None
EP_IN  = None

print("Scanning USB descriptors...")

for cfg in device:
    for intf in cfg:
        for setting in intf:
            if setting.getNumber() != INTERFACE_NUM:
                continue

            for ep in setting:
                addr = ep.getAddress()
                direction = "IN" if addr & 0x80 else "OUT"
                print(f"  Interface {INTERFACE_NUM} EP 0x{addr:02X} ({direction})")

                if addr & 0x80:
                    EP_IN = addr
                else:
                    EP_OUT = addr

if EP_OUT is None or EP_IN is None:
    raise RuntimeError("Could not find both IN and OUT endpoints")

print(f"Using EP_OUT=0x{EP_OUT:02X}, EP_IN=0x{EP_IN:02X}")
print("Connected to Nano ESP32 USB I/O")

counter = 0
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
color_idx = 0

try:
    while True:
        r, g, b = colors[color_idx]

        out_buf = bytearray(OUT_SIZE)
        struct.pack_into(
            OUT_FMT,
            out_buf,
            0,
            1,          # enable
            r, g, b,
            counter
        )

        handle.bulkWrite(EP_OUT, out_buf, timeout=100)

        in_buf = handle.bulkRead(EP_IN, IN_SIZE, timeout=100)
        status, echo = struct.unpack_from(IN_FMT, in_buf, 0)

        print(f"status={status} echo={echo}")

        counter += 1
        color_idx = (color_idx + 1) % len(colors)
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    handle.releaseInterface(INTERFACE_NUM)
    handle.close()
    ctx.exit()
