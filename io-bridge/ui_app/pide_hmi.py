import sys
import time
import threading
import ctypes
import serial
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QComboBox
)
from PyQt6.QtCore import QTimer

import pyqtgraph as pg


# ---------------- CONFIG ----------------

PORT = "COM8"
BAUD = 500000
FRAME_SIZE = 256
MAGIC = 0xDEADBEEF

NOP_FLOAT_VALUE = -999.9
HISTORY_SEC = 60
PLOT_HZ = 5


# ---------------- ctypes (MATCH usb_rgb_poll.py EXACTLY) ----------------

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
        ("_pad1", ctypes.c_uint8),
        ("_pad2", ctypes.c_uint8),
        ("_pad3", ctypes.c_uint8),
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


# ---------------- USB WORKER ----------------

class UsbWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

        self.out_buf = bytearray(FRAME_SIZE)
        self.in_buf  = bytearray(FRAME_SIZE)

        self.outAsm = OutAssembly.from_buffer(self.out_buf)
        self.inAsm  = InAssembly.from_buffer(self.in_buf)

        # Initialize outbound values to NOP
        self.outAsm.htr1_pide_ctrl.set_Sp = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_Cv = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_Kd = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_Kp = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_Ki = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_PvMin = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_PvMax = NOP_FLOAT_VALUE
        self.outAsm.htr1_pide_ctrl.set_Mode = 0xFF

        self.rx = bytearray()

    def run(self):
        with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.2)

            while self.running:
                # ----- transmit -----
                self.outAsm.magic = MAGIC
                self.outAsm.watchdog_out = self.inAsm.watchdog_in & 0xFF
                self.outAsm.command_bits.raw = 0

                ser.write(self.out_buf)
                ser.flush()

                # ----- receive / accumulate -----
                self.rx += ser.read(128)

                # ----- parse frames -----
                while len(self.rx) >= FRAME_SIZE:
                    magic = int.from_bytes(self.rx[0:4], "little")
                    if magic != MAGIC:
                        self.rx.pop(0)
                        continue

                    frame = self.rx[:FRAME_SIZE]
                    self.rx = self.rx[FRAME_SIZE:]
                    self.in_buf[:] = frame

                time.sleep(0.01)

    def stop(self):
        self.running = False


# ---------------- UI ----------------

class PideHMI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PIDE HMI")

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

        # ---------- STATUS BAR ----------
        status = QHBoxLayout()

        self.lbl_mode = QLabel("Mode: --")
        self.lbl_kp   = QLabel("Kp: --")
        self.lbl_ki   = QLabel("Ki: --")
        self.lbl_kd   = QLabel("Kd: --")

        for lbl in (self.lbl_mode, self.lbl_kp, self.lbl_ki, self.lbl_kd):
            lbl.setMinimumWidth(120)
            status.addWidget(lbl)

        status.addStretch()
        layout.addLayout(status)

        # ---------- PLOT ----------
        self.plot = pg.PlotWidget(title=f"Last {HISTORY_SEC}s")
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)

        self.sp_curve = self.plot.plot(pen="y", name="SP")
        self.pv_curve = self.plot.plot(pen="g", name="PV")
        self.cv_curve = self.plot.plot(pen="r", name="CV")

        layout.addWidget(self.plot)

        # ---------- CONTROLS ----------
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

    def set_sp(self, v): self.worker.outAsm.htr1_pide_ctrl.set_Sp = float(v)
    def set_cv(self, v): self.worker.outAsm.htr1_pide_ctrl.set_Cv = float(v)
    def set_kp(self, v): self.worker.outAsm.htr1_pide_ctrl.set_Kp = float(v)
    def set_ki(self, v): self.worker.outAsm.htr1_pide_ctrl.set_Ki = float(v)
    def set_kd(self, v): self.worker.outAsm.htr1_pide_ctrl.set_Kd = float(v)
    def set_mode(self, idx): self.worker.outAsm.htr1_pide_ctrl.set_Mode = idx & 0xFF

    # ---------- update ----------

    def update_ui(self):
        now = time.time() - self.t0
        stat = self.worker.inAsm.htr1_pide_stat

        # update status labels
        self.lbl_mode.setText(f"Mode: {stat.Mode}")
        self.lbl_kp.setText(f"Kp: {stat.Kp:.3f}")
        self.lbl_ki.setText(f"Ki: {stat.Ki:.3f}")
        self.lbl_kd.setText(f"Kd: {stat.Kd:.3f}")

        # append plot data
        self.ts.append(now)
        self.sp.append(stat.Sp)
        self.pv.append(stat.Pv)
        self.cv.append(stat.Cv)

        cutoff = now - HISTORY_SEC
        while self.ts and self.ts[0] < cutoff:
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
    w.resize(1100, 650)
    w.show()
    sys.exit(app.exec())
