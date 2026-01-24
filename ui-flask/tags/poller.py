# tags/poller.py

import time
import struct
from collections import defaultdict, deque

from tags.usb_comm import UsbComm
from tags.registry import group_tags_by_command
from tags.state import (
    get_subscriptions,
    update_tag,
)

# ---------------- Protocol framing ----------------

MAGIC = 0xDEADBEEF
HEADER_FMT = "<I H B B B B"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

RESPONSE_TIMEOUT = 0.15
MAX_RETRIES = 3


class Poller:
    def __init__(
        self,
        usb: UsbComm,
        poll_interval: float = 0.2,  # seconds
    ):
        self.usb = usb
        self.poll_interval = poll_interval
        self.running = False

        self.seq = 0
        self.rx = bytearray()

        # Write command queue (runtime → poller)
        self.write_queue = deque()

    # ------------------------------------------------
    # Public API (used by runtime)
    # ------------------------------------------------

    def enqueue_write(self, obj_id: int, cmd_id: int, payload: bytes = b""):
        """
        Enqueue a write command.
        Writes always take priority over reads.
        """
        self.write_queue.append((obj_id, cmd_id, payload))

    # ------------------------------------------------
    # Frame helpers
    # ------------------------------------------------

    def _build_frame(self, obj_id: int, cmd_id: int, payload: bytes = b"") -> bytes:
        self.seq = (self.seq + 1) & 0xFF
        length = HEADER_SIZE + len(payload)

        header = struct.pack(
            HEADER_FMT,
            MAGIC,
            length,
            self.seq,
            obj_id,
            cmd_id,
            0
        )

        return header + payload

    def _send_and_recv(self, frame: bytes) -> bytes | None:
        """
        Send frame and wait for matching response.
        Returns payload or None on timeout.
        """
        for _ in range(MAX_RETRIES):
            self.usb.send(frame)
            t0 = time.time()

            while time.time() - t0 < RESPONSE_TIMEOUT:
                self.rx += self.usb.read(512)

                while len(self.rx) >= HEADER_SIZE:
                    # Resync on MAGIC
                    if struct.unpack("<I", self.rx[:4])[0] != MAGIC:
                        del self.rx[0]
                        continue

                    length = struct.unpack("<H", self.rx[4:6])[0]
                    if len(self.rx) < length:
                        break

                    frame = self.rx[:length]
                    del self.rx[:length]

                    _, _, seq, obj, cmd, _ = struct.unpack(
                        HEADER_FMT, frame[:HEADER_SIZE]
                    )

                    if seq == self.seq:
                        return frame[HEADER_SIZE:length]

            # retry
        return None

    # ------------------------------------------------
    # Main loop
    # ------------------------------------------------

    def run(self):
        self.running = True
        print("[poller] started")

        while self.running:
            start = time.time()

            # ------------------------------------------------
            # 1) WRITE PHASE (highest priority)
            # ------------------------------------------------
            if self.write_queue:
                obj_id, cmd_id, payload = self.write_queue.popleft()
                frame = self._build_frame(obj_id, cmd_id, payload)

                payload_rx = self._send_and_recv(frame)
                if payload_rx is None:
                    # Write failed / timed out — log if desired
                    # print(f"[poller] WRITE timeout obj={obj_id} cmd={cmd_id}")
                    pass

                # Do NOT return early — allow multiple writes per cycle
                continue

            # ------------------------------------------------
            # 2) READ / POLL PHASE
            # ------------------------------------------------
            subs = get_subscriptions()
            if not subs:
                time.sleep(self.poll_interval)
                continue

            # Collate tags → (obj_id, cmd_id)
            groups = group_tags_by_command(list(subs))

            for (obj_id, cmd_id), tags in groups.items():
                frame = self._build_frame(obj_id, cmd_id)
                payload = self._send_and_recv(frame)

                if payload is None:
                    # print(f"[poller] no response obj={obj_id} cmd={cmd_id}")
                    continue

                for tag in tags:
                    try:
                        value = tag.parser(payload)
                        update_tag(tag.name, value)
                        # print(f"[poller] {tag.name} = {value}")
                    except Exception as e:
                        print(f"[poller] parse error {tag.name}: {e}")

            # ------------------------------------------------
            # Maintain poll rate
            # ------------------------------------------------
            dt = time.time() - start
            if dt < self.poll_interval:
                time.sleep(self.poll_interval - dt)

        print("[poller] stopped")

    def stop(self):
        self.running = False
