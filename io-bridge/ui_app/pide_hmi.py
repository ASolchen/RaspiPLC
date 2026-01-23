import sys
import time
import threading
import struct
import serial
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QComboBox
)
from PyQt6.QtCore import QTimer

import pyqtgraph as pg


# ================== CONFIG ==================

PORT = "COM8"
BAUD = 500000

MAGIC = 0xDEADBEEF

HEADER_FMT = "<I H B B B B"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

OBJ_PID1 = 1

PID_CMD = {"READ_STATUS" : 0x01,
    "SP"  : 0x10,
    "CV"   : 0x11,
    "KP"   : 0x12,
    "KI"    : 0x13,
    "KD"   : 0x14,
    "PVMIN" : 0x15,
    "PVMAX" : 0x16,
    "MODE"  : 0x17}

PLOT_HZ = 10
HISTORY_SEC = 300

RESPONSE_TIMEOUT = 0.15
MAX_RETRIES = 5


# ================== STRUCTS ==================

PID_STATUS_FMT = "<9f B 3x"
PID_STATUS_SIZE = struct.calcsize(PID_STATUS_FMT)


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
        self.pid_status = None

    # ---------- framing ----------

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

    # ---------- UI API ----------

    def enqueue(self, cmd_id, payload=b""):
        with self.lock:
            self.cmd_queue.append((cmd_id, payload))
            #print(f"[UI] Queued cmd={cmd_id}")

    # ---------- thread ----------

    def run(self):
        with serial.Serial(PORT, BAUD, timeout=0.05) as ser:
            self.ser = ser
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            last_poll = 0.0

            while self.running:
                now = time.time()

                # -------- scheduler --------
                with self.lock:
                    # If nothing in flight, choose next command
                    if self.in_flight is None:
                        if self.cmd_queue:
                            cmd_id, payload = self.cmd_queue.popleft()
                            seq, frame = self.build_frame(OBJ_PID1, cmd_id, payload)
                            self.in_flight = {
                                "seq": seq,
                                "cmd": cmd_id,
                                "frame": frame,
                                "ts": 0.0,
                                "retries": 0
                            }
                            #print(f"[SCHED] Sending queued cmd={cmd_id} seq={seq}")

                        elif now - last_poll > 1.0 / PLOT_HZ:
                            last_poll = now
                            seq, frame = self.build_frame(OBJ_PID1, PID_CMD["READ_STATUS"])
                            self.in_flight = {
                                "seq": seq,
                                "cmd": PID_CMD["READ_STATUS"],
                                "frame": frame,
                                "ts": 0.0,
                                "retries": 0
                            }
                            #print(f"[SCHED] Polling READ_STATUS seq={seq}")

                    # Transmit / retry in-flight
                    if self.in_flight:
                        if (
                            self.in_flight["retries"] == 0 or
                            (now - self.in_flight["ts"]) > RESPONSE_TIMEOUT
                        ):
                            self.ser.write(self.in_flight["frame"])
                            self.ser.flush()

                            self.in_flight["ts"] = now
                            self.in_flight["retries"] += 1

                            if self.in_flight["retries"] > MAX_RETRIES:
                                #print(f"[DROP] cmd={self.in_flight['cmd']}")
                                self.in_flight = None

                # -------- RX --------
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

                    magic, _, seq, obj, cmd, _ = struct.unpack(
                        HEADER_FMT, frame[:HEADER_SIZE]
                    )
                    payload = frame[HEADER_SIZE:length]

                    with self.lock:
                        if self.in_flight and seq == self.in_flight["seq"]:
                            #print(f"[RX] Ack cmd={cmd} seq={seq}")
                            self.in_flight = None

                    if cmd == PID_CMD["READ_STATUS"] and len(payload) == PID_STATUS_SIZE:
                        self.pid_status = struct.unpack(PID_STATUS_FMT, payload)

                time.sleep(0.01)

    def stop(self):
        self.running = False


# ================== UI ==================

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

        status = QHBoxLayout()
        self.lbl_mode = QLabel("Mode: --")
        self.lbl_kp = QLabel("Kp: --")
        self.lbl_ki = QLabel("Ki: --")
        self.lbl_kd = QLabel("Kd: --")

        for l in (self.lbl_mode, self.lbl_kp, self.lbl_ki, self.lbl_kd):
            l.setMinimumWidth(120)
            status.addWidget(l)

        layout.addLayout(status)

        self.plot = pg.PlotWidget(title=f"Last {HISTORY_SEC}s")
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)

        self.sp_curve = self.plot.plot(pen="y", name="SP")
        self.pv_curve = self.plot.plot(pen="g", name="PV")
        self.cv_curve = self.plot.plot(pen="r", name="CV")

        layout.addWidget(self.plot)

        ctrl = QHBoxLayout()
        self._spin(ctrl, "SP", PID_CMD["SP"])
        self._spin(ctrl, "Kp", PID_CMD["KP"])
        self._spin(ctrl, "Ki", PID_CMD["KI"])
        self._spin(ctrl, "Kd", PID_CMD["KD"])

        self.mode = QComboBox()
        self.mode.addItems(["OFF", "MAN", "AUTO"])
        self.mode.currentIndexChanged.connect(
            lambda i: self.worker.enqueue(PID_CMD["MODE"], struct.pack("<B", i))
        )
        ctrl.addWidget(QLabel("Mode"))
        ctrl.addWidget(self.mode)

        layout.addLayout(ctrl)

    def _spin(self, layout, name, cmd):
        layout.addWidget(QLabel(name))
        box = QDoubleSpinBox()
        box.setRange(-10000, 10000)
        box.setDecimals(3)
        box.editingFinished.connect(
            lambda b=box, c=cmd:
                self.worker.enqueue(c, struct.pack("<f", b.value()))
        )
        layout.addWidget(box)

    def update_ui(self):
        st = self.worker.pid_status
        if not st:
            return

        Sp, Pv, Cv, Kp, Ki, Kd, PvMin, PvMax, Err, Mode = st
        now = time.time() - self.t0

        self.lbl_mode.setText(f"Mode: {int(Mode)}")
        self.lbl_kp.setText(f"Kp: {Kp:.3f}")
        self.lbl_ki.setText(f"Ki: {Ki:.3f}")
        self.lbl_kd.setText(f"Kd: {Kd:.3f}")

        self.ts.append(now)
        self.sp.append(Sp)
        self.pv.append(Pv)
        self.cv.append(Cv)

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


# ================== MAIN ==================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = PideHMI()
    w.resize(1100, 650)
    w.show()
    sys.exit(app.exec())
