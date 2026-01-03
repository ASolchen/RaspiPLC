#!/usr/bin/env python3
"""
shmctrl - Python client library for RaspiPLC shared memory service

This is intentionally importable by other services (plc-runtime, ui-flask, etc.).
It does NOT mmap shared memory and does NOT know offsets; it only talks to shm-service
over the Unix domain socket.
"""

import json
import socket
from typing import Any, Dict, List, Optional

SOCKET_PATH = "/run/raspiplc-shm.sock"


class ShmCtrl:
    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path

    def _send(self, req: Dict[str, Any]) -> Dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)
            sock.sendall(json.dumps(req).encode())
            data = sock.recv(8192)

        if not data:
            raise RuntimeError("No response from shm-service")

        return json.loads(data.decode())

    def read(self, tags: List[str]) -> Dict[str, Any]:
        resp = self._send({"read": tags})
        # service responds like: {"read": {...}}
        return resp.get("read", resp)

    def write(self, values: Dict[str, Any]) -> Dict[str, Any]:
        # service responds like: {"status":"ok"}
        return self._send({"write": values})

    def reload(self) -> Dict[str, Any]:
        # service responds like: {"status":"reloaded"}
        return self._send({"reload": True})
