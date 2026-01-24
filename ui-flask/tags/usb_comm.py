# usb_comm.py
import serial

class UsbComm:
    def __init__(self, port, baud):
        self.ser = serial.Serial(
            port,
            baud,
            timeout=0.05,
            dsrdtr=False,
            rtscts=False,
        )
        self.ser.setDTR(False)
        self.ser.setRTS(False)

    def send(self, frame: bytes):
        self.ser.write(frame)
        self.ser.flush()

    def read(self, n=512) -> bytes:
        return self.ser.read(n)

    def close(self):
        self.ser.close()

