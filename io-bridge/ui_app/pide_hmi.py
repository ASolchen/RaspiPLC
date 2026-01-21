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

HISTORY_SEC = 60
PLOT_HZ = 5

SET_BITS = {
    "Sp": 0,
    "Cv": 1,
    "Kp": 2,
    "Ki": 3,
    "Kd": 4,
    "PvMin": 5,
    "PvMax": 6,
    "Mode": 7
}

def BIT(n: int) -> int:
    return 1 << n

def mask_for(key: str) -> int:
    return BIT(SET_BITS[key])


# ---------------- ctypes (MUST MATCH ESP PACKED STRUCTS) ----------------
# NOTE: These structures MUST total FRAME_SIZE bytes on the wire.
# The ESP side now hard-pads the in/out assemblies to 256 bytes.

class UsbCommCmdBits(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("raw", ctypes.c_uint32)]


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
        ("magic",         ctypes.c_uint32),
        ("watchdog_in",   ctypes.c_uint8),
        ("pad5",          ctypes.c_uint8),
        ("pad6",          ctypes.c_uint8),
        ("pad7",          ctypes.c_uint8),
        ("temp1",         ctypes.c_float),
        ("temp2",         ctypes.c_float),
        ("heater1",       ctypes.c_float),
        ("heater2",       ctypes.c_float),
        ("htr1_pide_stat", PideStat),
        ("_reserved",     ctypes.c_uint8 * (FRAME_SIZE - (4 + 1 + 3 + 4*4 + ctypes.sizeof(PideStat)))),
    ]


class PideCtrl(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("setBits",    ctypes.c_uint32),
        ("set_Sp",     ctypes.c_float),
        ("set_Cv",     ctypes.c_float),
        ("set_Kp",     ctypes.c_float),
        ("set_Ki",     ctypes.c_float),
        ("set_Kd",     ctypes.c_float),
        ("set_PvMin",  ctypes.c_float),
        ("set_PvMax",  ctypes.c_float),
        ("set_Mode",   ctypes.c_uint8),
        ("_pad65",     ctypes.c_uint8),
        ("_pad66",     ctypes.c_uint8),
        ("_pad67",     ctypes.c_uint8),
    ]


class OutAssembly(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic",         ctypes.c_uint32),
        ("watchdog_out",  ctypes.c_uint8),
        ("pad5",          ctypes.c_uint8),
        ("pad6",          ctypes.c_uint8),
        ("pad7",          ctypes.c_uint8),
        ("command_bits",  UsbCommCmdBits),
        ("htr1_pide_ctrl", PideCtrl),
        ("_reserved",     ctypes.c_uint8 * (FRAME_SIZE - (4 + 1 + 3 + ctypes.sizeof(UsbCommCmdBits) + ctypes.sizeof(PideCtrl)))),
    ]


assert ctypes.sizeof(InAssembly) == FRAME_SIZE, f"InAssembly is {ctypes.sizeof(InAssembly)} bytes, expected {FRAME_SIZE}"
assert ctypes.sizeof(OutAssembly) == FRAME_SIZE, f"OutAssembly is {ctypes.sizeof(OutAssembly)} bytes, expected {FRAME_SIZE}"


# ---------------- USB WORKER ----------------
# Protocol semantics used here:
# - setBits is VALID ONLY FOR THE ONE FRAME SENT.
# - UI thread queues pending changes into a mask+values.
# - Worker thread snapshots pending values into the outgoing frame,
#   sets setBits for that one frame, sends, then clears (by resetting pending mask).


class UsbWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

        self.out_buf = bytearray(FRAME_SIZE)
        self.in_buf  = bytearray(FRAME_SIZE)

        self.outAsm = OutAssembly.from_buffer(self.out_buf)
        self.inAsm  = InAssembly.from_buffer(self.in_buf)

        # TX synchronization / mailbox
        self.tx_lock = threading.Lock()
        self.pending_mask = 0

        # RX stream buffer for resync
        self.rx = bytearray()

        # Initialize outbound defaults (device will apply only if we set setBits)
        with self.tx_lock:
            self.outAsm.magic = MAGIC
            self.outAsm.watchdog_out = 0
            self.outAsm.command_bits.raw = 0

            self.outAsm.htr1_pide_ctrl.setBits = 0
            # self.outAsm.htr1_pide_ctrl.set_Sp = 100.0
            # self.outAsm.htr1_pide_ctrl.set_Cv = 0.0
            # self.outAsm.htr1_pide_ctrl.set_Kp = 2.0
            # self.outAsm.htr1_pide_ctrl.set_Ki = 0.1
            # self.outAsm.htr1_pide_ctrl.set_Kd = 0.0
            # self.outAsm.htr1_pide_ctrl.set_PvMin = 0.0
            # self.outAsm.htr1_pide_ctrl.set_PvMax = 500.0
            # self.outAsm.htr1_pide_ctrl.set_Mode = 2  # AUTO

            # If you want to force initial apply on startup, queue them:
            # self.pending_mask |= mask_for("Sp")
            # self.pending_mask |= mask_for("Kp")
            # self.pending_mask |= mask_for("Ki")
            # self.pending_mask |= mask_for("Kd")
            # self.pending_mask |= mask_for("PvMin")
            # self.pending_mask |= mask_for("PvMax")
            # self.pending_mask |= mask_for("Mode")

    # ---- API for UI thread (queue changes) ----
    def queue_set(self, key: str, value):
        with self.tx_lock:
            if key == "Sp":
                self.outAsm.htr1_pide_ctrl.set_Sp = float(value)
            elif key == "Cv":
                self.outAsm.htr1_pide_ctrl.set_Cv = float(value)
            elif key == "Kp":
                self.outAsm.htr1_pide_ctrl.set_Kp = float(value)
            elif key == "Ki":
                self.outAsm.htr1_pide_ctrl.set_Ki = float(value)
            elif key == "Kd":
                self.outAsm.htr1_pide_ctrl.set_Kd = float(value)
            elif key == "PvMin":
                self.outAsm.htr1_pide_ctrl.set_PvMin = float(value)
            elif key == "PvMax":
                self.outAsm.htr1_pide_ctrl.set_PvMax = float(value)
            elif key == "Mode":
                self.outAsm.htr1_pide_ctrl.set_Mode = int(value) & 0xFF
                print(f"Mode -> {value}")
            else:
                return
            self.pending_mask |= mask_for(key)

    def run(self):
        with serial.Serial(PORT, BAUD, timeout=0.05, write_timeout=1) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.2)

            while self.running:
                # ----- build TX frame (atomic snapshot) -----
                with self.tx_lock:
                    self.outAsm.magic = MAGIC
                    self.outAsm.watchdog_out = self.inAsm.watchdog_in & 0xFF
                    self.outAsm.command_bits.raw = 0

                    # setBits is valid ONLY for this frame
                    self.outAsm.htr1_pide_ctrl.setBits = self.pending_mask & 0xFFFFFFFF
                    self.pending_mask = 0

                    frame = bytes(self.out_buf)  # immutable snapshot

                # ----- transmit -----
                try:
                    ser.write(frame)
                    # flush() waits for OS buffer; not a true on-wire guarantee, but ok
                    ser.flush()
                except serial.SerialTimeoutException:
                    # treat as dropped TX; continue
                    pass

                # ----- receive / accumulate -----
                # Read a chunk; USB CDC often delivers 64-byte packets
                chunk = ser.read(512)
                if chunk:
                    self.rx += chunk

                # ----- parse frames (magic resync like ESP) -----
                # Strategy: scan for MAGIC at rx[0:4]; if mismatch, drop 1 byte and continue.
                while len(self.rx) >= 4:
                    if int.from_bytes(self.rx[0:4], "little") == MAGIC:
                        if len(self.rx) < FRAME_SIZE:
                            break
                        frame_in = self.rx[:FRAME_SIZE]
                        del self.rx[:FRAME_SIZE]
                        self.in_buf[:] = frame_in
                    else:
                        del self.rx[0]

                # Keep RX buffer bounded (defensive)
                if len(self.rx) > 8192:
                    self.rx = self.rx[-4096:]

                # Small sleep to reduce CPU; comms still run fast enough
                time.sleep(0.02)

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
        self.lbl_temp1 = QLabel("Temp1: --")
        self.lbl_temp2 = QLabel("Temp2: --")

        for lbl in (self.lbl_mode, self.lbl_kp, self.lbl_ki, self.lbl_kd, self.lbl_temp1, self.lbl_temp2):
            lbl.setMinimumWidth(130)
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

        self.sp_box = self._spin("SP", ctrl, lambda v: self.worker.queue_set("Sp", v))
        self.cv_box = self._spin("CV", ctrl, lambda v: self.worker.queue_set("Cv", v))
        self.kp_box = self._spin("Kp", ctrl, lambda v: self.worker.queue_set("Kp", v))
        self.ki_box = self._spin("Ki", ctrl, lambda v: self.worker.queue_set("Ki", v))
        self.kd_box = self._spin("Kd", ctrl, lambda v: self.worker.queue_set("Kd", v))

        self.mode = QComboBox()
        self.mode.addItems(["OFF", "MAN", "AUTO"])
        self.mode.currentIndexChanged.connect(lambda idx: self.worker.queue_set("Mode", idx))
        ctrl.addWidget(QLabel("Mode"))
        ctrl.addWidget(self.mode)

        layout.addLayout(ctrl)

    def _spin(self, name, layout, cb):
        layout.addWidget(QLabel(name))
        box = QDoubleSpinBox()
        box.setRange(-10000, 10000)
        box.setDecimals(3)
        box.setSingleStep(1.0)
        box.editingFinished.connect(lambda b=box: cb(b.value()))
        layout.addWidget(box)
        return box

    def update_ui(self):
        now = time.time() - self.t0

        stat = self.worker.inAsm.htr1_pide_stat
        temp1 = float(self.worker.inAsm.temp1)
        temp2 = float(self.worker.inAsm.temp2)

        # status labels
        self.lbl_mode.setText(f"Mode: {int(stat.Mode)}")
        self.lbl_kp.setText(f"Kp: {stat.Kp:.3f}")
        self.lbl_ki.setText(f"Ki: {stat.Ki:.3f}")
        self.lbl_kd.setText(f"Kd: {stat.Kd:.3f}")
        self.lbl_temp1.setText(f"Temp1: {temp1:.1f}")
        self.lbl_temp2.setText(f"Temp2: {temp2:.1f}")

        # plot buffers
        self.ts.append(now)
        self.sp.append(float(stat.Sp))
        self.pv.append(float(stat.Pv))
        self.cv.append(float(stat.Cv))

        cutoff = now - HISTORY_SEC
        while self.ts and self.ts[0] < cutoff:
            self.ts.popleft(); self.sp.popleft(); self.pv.popleft(); self.cv.popleft()

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
