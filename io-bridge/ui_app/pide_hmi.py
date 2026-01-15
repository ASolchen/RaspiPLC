import sys
import time
import threading
import ctypes
import serial
from collections import deque
#pip install pyqt6 pyqtgraph pyserial

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QDoubleSpinBox, QComboBox
)
from PyQt6.QtCore import QTimer

import pyqtgraph as pg


# ---------------- CONFIG ----------------

PORT = "COM6"
BAUD = 1500000
FRAME_SIZE = 256
MAGIC = 0xDEADBEEF

NOP_FLOAT = -999.9

HISTORY_SEC = 3600
PLOT_HZ = 5


# ---------------- ctypes (MATCH YOUR WORKING FILE) ----------------

class PideStat(ctypes.Structure):
    _fields_ = [
        ("Sp", ctypes.c_float),
        ("Pv", ctypes.c_float),
        ("Cv", ctypes.c_float),
        ("Kp", ctypes.c_float),
        ("Ki", ctypes.c_float),
        ("Kd", ctypes.c_float),
        ("PvMin", ctypes.c_float),
        ("PvMax", ctypes.c_float),
        ("Err", ctypes.c_float),
        ("Mode", ctypes.c_uint8),
    ]


class InAssembly(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("watchdog", ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * 3),
        ("temp1", ctypes.c_float),
        ("temp2", ctypes.c_float),
        ("heater1", ctypes.c_float),
        ("heater2", ctypes.c_float),
        ("pide", PideStat),
    ]


class PideCtrl(ctypes.Structure):
    _fields_ = [
        ("set_Sp", ctypes.c_float),
        ("set_Pv", ctypes.c_float),
        ("set_Kd", ctypes.c_float),
        ("set_Kp", ctypes.c_float),
        ("set_Ki", ctypes.c_float),
        ("set_PvMin", ctypes.c_float),
        ("set_PvMax", ctypes.c_float),
        ("set_Mode", ctypes.c_uint8),
    ]


class OutAssembly(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("watchdog", ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * 3),
        ("pide", PideCtrl),
    ]


# ---------------- USB WORKER ----------------

class UsbWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

        self.out_buf = bytearray(FRAME_SIZE)
        self.in_buf = bytearray(FRAME_SIZE)

        self.outAsm = OutAssembly.from_buffer(self.out_buf)
        self.inAsm = InAssembly.from_buffer(self.in_buf)

        # Initialize all set_* fields to NOP (floats) and Mode to a sane default
        for name, ctype in PideCtrl._fields_:
            if ctype is ctypes.c_uint8:
                setattr(self.outAsm.pide, name, 2)          # PID_OFF by default
            elif ctype is ctypes.c_float:
                setattr(self.outAsm.pide, name, 55.5)#NOP_FLOAT)  # sentinel for "no update"
            else:
                # fallback: try zero
                setattr(self.outAsm.pide, name, 0)


    def run(self):
        with serial.Serial(PORT, BAUD, timeout=1) as ser:
            while self.running:
                self.outAsm.magic = MAGIC
                ser.write(self.out_buf)
                ser.readinto(self.in_buf)
                time.sleep(0.01)

    def stop(self):
        self.running = False


# ---------------- UI ----------------

class PideHMI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PIDE HMI (PyQt6)")

        self.worker = UsbWorker()
        self.worker.start()

        self.t0 = time.time()

        self.ts = deque()
        self.sp = deque()
        self.pv = deque()
        self.cv = deque()

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(int(1000 / PLOT_HZ))

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.plot = pg.PlotWidget(title="Last Hour")
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)

        self.sp_curve = self.plot.plot(pen="y", name="SP")
        self.pv_curve = self.plot.plot(pen="g", name="PV")
        self.cv_curve = self.plot.plot(pen="r", name="CV")

        layout.addWidget(self.plot)

        ctrl = QHBoxLayout()

        self.sp_box = self._spin("SP", ctrl, self.set_sp)
        self.cv_box = self._spin("CV", ctrl, self.set_cv)
        self.kp_box = self._spin("Kp", ctrl, self.set_kp)
        self.ki_box = self._spin("Ki", ctrl, self.set_ki)
        self.kd_box = self._spin("Kd", ctrl, self.set_kd)

        self.mode = QComboBox()
        self.mode.addItems(["OFF", "MAN", "AUTO"])
        self.mode.currentIndexChanged.connect(self.set_mode)
        ctrl.addWidget(QLabel("Mode"))
        ctrl.addWidget(self.mode)

        layout.addLayout(ctrl)

    def _spin(self, name, layout, cb):
        layout.addWidget(QLabel(name))
        box = QDoubleSpinBox()
        box.setRange(-10000, 10000)
        box.setDecimals(3)
        box.editingFinished.connect(lambda b=box: cb(b.value()))
        layout.addWidget(box)
        return box

    # ---------- setters ----------

    def set_sp(self, v):
        self.worker.outAsm.pide.set_Sp = v

    def set_cv(self, v):
        self.worker.outAsm.pide.set_Cv = v

    def set_kp(self, v):
        self.worker.outAsm.pide.set_Kp = v

    def set_ki(self, v):
        self.worker.outAsm.pide.set_Ki = v

    def set_kd(self, v):
        self.worker.outAsm.pide.set_Kd = v

    def set_mode(self, idx):
        self.worker.outAsm.pide.set_Mode = idx

    # ---------- update ----------

    def update_ui(self):
        now = time.time() - self.t0
        stat = self.worker.inAsm.pide

        self.ts.append(now)
        self.sp.append(stat.Sp)
        self.pv.append(stat.Pv)
        self.cv.append(stat.Cv)

        while self.ts and self.ts[0] < now - HISTORY_SEC:
            self.ts.popleft()
            self.sp.popleft()
            self.pv.popleft()
            self.cv.popleft()

        self.sp_curve.setData(self.ts, self.sp)
        self.pv_curve.setData(self.ts, self.pv)
        self.cv_curve.setData(self.ts, self.cv)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = PideHMI()
    w.resize(1000, 600)
    w.show()
    sys.exit(app.exec())
