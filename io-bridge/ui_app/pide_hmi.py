import sys
import time
import threading
import struct
import serial
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import QTimer

import pyqtgraph as pg


# ================== CONFIG ==================

PORT = "COM8"
BAUD = 500000

MAGIC = 0xDEADBEEF

HEADER_FMT = "<I H B B B B"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

OBJ_TIC1 = 1

TC_CMD = {
    "READ_STATUS": 0x01,
    "SET_MODE":    0x20,
    "SET_SP":      0x21,
    "SET_CTRL":    0x22,
}

PID_CMD = {
    "SP":    0x10,
    "CV":    0x11,
    "KP":    0x12,
    "KI":    0x13,
    "KD":    0x14,
    "PVMIN": 0x15,
    "PVMAX": 0x16,
    "MODE":  0x17,
}

PLOT_HZ = 10
HISTORY_SEC = 1800

RESPONSE_TIMEOUT = 0.15
MAX_RETRIES = 5


# ================== STRUCTS ==================

PID_STATUS_FMT = "<9f B 3x"
PID_STATUS_SIZE = struct.calcsize(PID_STATUS_FMT)

# TempCtrl:
# u8 Mode
# u8 CtrlMode
# u16 pad
# float TempCtrl.Sp
# pide_stat_t
TC_STATUS_FMT = "<B B H f " + PID_STATUS_FMT[1:]
TC_STATUS_SIZE = struct.calcsize(TC_STATUS_FMT)

TC_MODE_NAMES  = ["Off", "OperManual", "OperAuto", "PgmAuto"]
TC_CTRL_NAMES  = ["Off", "Boost", "FeedFwd", "ClosedLoop"]
PID_MODE_NAMES = ["OFF", "MAN", "AUTO"]


# ================== USB WORKER ==================

class UsbWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

        self.seq = 0
        self.lock = threading.Lock()

        self.cmd_queue = deque()
        self.in_flight = None

        self.rx = bytearray()
        self.tc_status = None

    def build_frame(self, obj_id, cmd_id, payload=b""):
        self.seq = (self.seq + 1) & 0xFF
        length = HEADER_SIZE + len(payload)
        hdr = struct.pack(
            HEADER_FMT,
            MAGIC,
            length,
            self.seq,
            obj_id,
            cmd_id,
            0
        )
        return self.seq, hdr + payload

    def enqueue(self, cmd_id, payload=b""):
        with self.lock:
            self.cmd_queue.append((cmd_id, payload))

    def run(self):
        with serial.Serial(PORT,
                           BAUD,
                           timeout=0.05,
                           dsrdtr=False,
                           rtscts=False) as ser:
            ser.setDTR(False)
            ser.setRTS(False)
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            last_poll = 0.0

            while self.running:
                now = time.time()

                with self.lock:
                    if self.in_flight is None:
                        if self.cmd_queue:
                            cmd_id, payload = self.cmd_queue.popleft()
                            seq, frame = self.build_frame(OBJ_TIC1, cmd_id, payload)
                            self.in_flight = {
                                "seq": seq,
                                "cmd": cmd_id,
                                "frame": frame,
                                "ts": 0.0,
                                "retries": 0
                            }
                        elif now - last_poll > 1.0 / PLOT_HZ:
                            last_poll = now
                            seq, frame = self.build_frame(OBJ_TIC1, TC_CMD["READ_STATUS"])
                            self.in_flight = {
                                "seq": seq,
                                "cmd": TC_CMD["READ_STATUS"],
                                "frame": frame,
                                "ts": 0.0,
                                "retries": 0
                            }

                    if self.in_flight:
                        if (
                            self.in_flight["retries"] == 0 or
                            (now - self.in_flight["ts"]) > RESPONSE_TIMEOUT
                        ):
                            ser.write(self.in_flight["frame"])
                            ser.flush()

                            self.in_flight["ts"] = now
                            self.in_flight["retries"] += 1

                            if self.in_flight["retries"] > MAX_RETRIES:
                                self.in_flight = None

                self.rx += ser.read(512)

                while len(self.rx) >= HEADER_SIZE:
                    if struct.unpack("<I", self.rx[:4])[0] != MAGIC:
                        del self.rx[0]
                        continue

                    length = struct.unpack("<H", self.rx[4:6])[0]
                    if len(self.rx) < length:
                        break

                    frame = self.rx[:length]
                    del self.rx[:length]

                    _, _, seq, _, cmd, _ = struct.unpack(
                        HEADER_FMT, frame[:HEADER_SIZE]
                    )
                    payload = frame[HEADER_SIZE:length]

                    with self.lock:
                        if self.in_flight and seq == self.in_flight["seq"]:
                            self.in_flight = None

                    if cmd == TC_CMD["READ_STATUS"] and len(payload) == TC_STATUS_SIZE:
                        self.tc_status = struct.unpack(TC_STATUS_FMT, payload)

                time.sleep(0.01)

    def stop(self):
        self.running = False


# ================== UI ==================

class TempCtrlHMI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TempCtrl HMI")

        self.worker = UsbWorker()
        self.worker.start()

        self.t0 = time.time()

        self.ts = deque()
        self.tc_sp = deque()
        self.pv = deque()
        self.cv = deque()

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(int(1000 / PLOT_HZ))

    def _build_ui(self):
        layout = QVBoxLayout(self)

        status = QHBoxLayout()
        self.lbl_tc_mode = QLabel("TC Mode: --")
        self.lbl_tc_ctrl = QLabel("CtrlMode: --")
        self.lbl_pid_mode = QLabel("PID Mode: --")
        self.lbl_kp = QLabel("Kp: --")
        self.lbl_ki = QLabel("Ki: --")
        self.lbl_kd = QLabel("Kd: --")

        for l in (self.lbl_tc_mode, self.lbl_tc_ctrl, self.lbl_pid_mode,
                  self.lbl_kp, self.lbl_ki, self.lbl_kd):
            l.setMinimumWidth(140)
            status.addWidget(l)

        layout.addLayout(status)

        self.plot = pg.PlotWidget(title=f"Last {HISTORY_SEC}s")
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)

        self.sp_curve = self.plot.plot(pen="y", name="TC SP")
        self.pv_curve = self.plot.plot(pen="g", name="PV")
        self.cv_curve = self.plot.plot(pen="r", name="CV")

        layout.addWidget(self.plot)

        controls = QHBoxLayout()

        tc_group = QGroupBox("TempCtrl")
        tc_layout = QHBoxLayout(tc_group)
        self._spin(tc_layout, "SP", TC_CMD["SET_SP"])
        self.tc_mode = QComboBox()
        self.tc_mode.addItems(TC_MODE_NAMES)
        self.tc_mode.currentIndexChanged.connect(
            lambda i: self.worker.enqueue(TC_CMD["SET_MODE"], struct.pack("<B", i))
        )
        tc_layout.addWidget(QLabel("Mode"))
        tc_layout.addWidget(self.tc_mode)
        controls.addWidget(tc_group)

        pid_group = QGroupBox("PIDE")
        pid_layout = QHBoxLayout(pid_group)
        self._spin(pid_layout, "Kp", PID_CMD["KP"])
        self._spin(pid_layout, "Ki", PID_CMD["KI"])
        self._spin(pid_layout, "Kd", PID_CMD["KD"])
        controls.addWidget(pid_group)

        layout.addLayout(controls)

    def _spin(self, layout, name, cmd):
        layout.addWidget(QLabel(name))
        box = QDoubleSpinBox()
        box.setRange(-10000, 10000)
        box.setDecimals(3)
        box.editingFinished.connect(
            lambda b=box, c=cmd:
                self.worker.enqueue(c, struct.pack("<f", float(b.value())))
        )
        layout.addWidget(box)

    def update_ui(self):
        st = self.worker.tc_status
        if not st:
            return

        (
            tc_mode, tc_ctrl, _pad, tc_sp,
            pid_sp, Pv, Cv, Kp, Ki, Kd, PvMin, PvMax, Err, pidMode
        ) = st

        now = time.time() - self.t0

        self.lbl_tc_mode.setText(f"TC Mode: {TC_MODE_NAMES[tc_mode]}")
        self.lbl_tc_ctrl.setText(f"CtrlMode: {TC_CTRL_NAMES[tc_ctrl]}")
        self.lbl_pid_mode.setText(f"PID Mode: {PID_MODE_NAMES[pidMode]}")
        self.lbl_kp.setText(f"Kp: {Kp:.3f}")
        self.lbl_ki.setText(f"Ki: {Ki:.3f}")
        self.lbl_kd.setText(f"Kd: {Kd:.3f}")

        self.ts.append(now)
        self.tc_sp.append(tc_sp)
        self.pv.append(Pv)
        self.cv.append(Cv)

        cutoff = now - HISTORY_SEC
        while self.ts and self.ts[0] < cutoff:
            self.ts.popleft()
            self.tc_sp.popleft()
            self.pv.popleft()
            self.cv.popleft()

        self.sp_curve.setData(self.ts, self.tc_sp)
        self.pv_curve.setData(self.ts, self.pv)
        self.cv_curve.setData(self.ts, self.cv)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


# ================== MAIN ==================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TempCtrlHMI()
    w.resize(1200, 700)
    w.show()
    sys.exit(app.exec())
