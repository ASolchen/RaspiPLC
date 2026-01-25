# usb_comm.py
import serial
import serial.serialutil
import time
import logging
log = logging.getLogger(__name__)

class UsbComm:
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connected = False

        self._open()

    # ------------------------------------------------------------

    def _open(self):
        try:
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=0.05,
                dsrdtr=False,
                rtscts=False,
            )
            self.ser.setDTR(False)
            self.ser.setRTS(False)
            self.connected = True
            log.info(f"[UsbComm] Connected to {self.port}")

        except serial.serialutil.SerialException as e:
            self.ser = None
            self.connected = False
            log.info(f"[UsbComm] Serial unavailable ({self.port}): {e}")

    # ------------------------------------------------------------

    def send(self, frame: bytes):
        if not self.connected:
            return

        try:
            self.ser.write(frame)
            self.ser.flush()

        except serial.serialutil.SerialException as e:
            log.info(f"[UsbComm] Write failed: {e}")
            self._handle_disconnect()

    # ------------------------------------------------------------

    def read(self, n=512) -> bytes:
        if not self.connected:
            return b""

        try:
            return self.ser.read(n)

        except serial.serialutil.SerialException as e:
            log.info(f"[UsbComm] Read failed: {e}")
            self._handle_disconnect()
            return b""

    # ------------------------------------------------------------

    def _handle_disconnect(self):
        log.info("[UsbComm] Serial disconnected")
        self.connected = False
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None

    # ------------------------------------------------------------

    def reconnect(self):
        if self.connected:
            return
        self._open()

    # ------------------------------------------------------------

    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None
            self.connected = False
