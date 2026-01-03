#!/usr/bin/env python3
"""
RaspiPLC Shared Memory Service

Long-running daemon that:
- Loads tag definitions from JSON
- Opens and mmaps shared memory regions
- Provides safe read/write access via IPC
- Supports hot-reload of tag layout

This service NEVER creates or resizes shared memory.
That responsibility belongs to shm-core.
"""

import os
import json
import mmap
import socket
import struct
import threading
from pathlib import Path
from typing import Dict, Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOCKET_PATH = "/run/raspiplc-shm.sock"
DEFAULT_TAGS_FILE = "/etc/raspiplc/tags.json"

# ---------------------------------------------------------------------------
# Type System (authoritative)
# ---------------------------------------------------------------------------

# name -> (struct_format, size)
TYPES = {
    "bool":    ("?", 1),
    "uint8":   ("B", 1),
    "int8":    ("b", 1),
    "uint16":  ("H", 2),
    "int16":   ("h", 2),
    "uint32":  ("I", 4),
    "int32":   ("i", 4),
    "float32": ("f", 4),
    "float64": ("d", 8),
}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

class Tag:
    def __init__(self, name: str, region: str, offset: int, type_name: str, scale: float = None):
        if type_name not in TYPES:
            raise ValueError(f"Unknown type '{type_name}'")

        self.name = name
        self.region = region
        self.offset = offset
        self.type_name = type_name
        self.struct_fmt, self.size = TYPES[type_name]
        self.scale = scale


# ---------------------------------------------------------------------------
# SHM Service
# ---------------------------------------------------------------------------

class SHMService:
    def __init__(self, tags_file: str):
        self.tags_file = tags_file
        self.regions: Dict[str, mmap.mmap] = {}
        self.tags: Dict[str, Tag] = {}
        self.lock = threading.Lock()

    # ---------------------------
    # Startup
    # ---------------------------

    def start(self):
        self._load_tags()
        self._open_socket()
        self._serve_forever()

    # ---------------------------
    # Tag Loading / Reload
    # ---------------------------

    def _load_tags(self):
        with open(self.tags_file, "r") as f:
            cfg = json.load(f)

        new_regions = {}
        new_tags = {}

        # Open SHM regions
        for name, info in cfg["regions"].items():
            path = info["path"]
            fd = os.open(path, os.O_RDWR)
            size = os.stat(path).st_size
            mm = mmap.mmap(fd, size)
            new_regions[name] = mm

        # Parse tags
        for tag_name, info in cfg["tags"].items():
            tag = Tag(
                name=tag_name,
                region=info["region"],
                offset=info["offset"],
                type_name=info["type"],
                scale=info.get("scale"),
            )

            region_mm = new_regions[tag.region]
            if tag.offset + tag.size > region_mm.size():
                raise ValueError(f"Tag '{tag_name}' exceeds region bounds")

            new_tags[tag_name] = tag

        # Atomic swap
        with self.lock:
            for mm in self.regions.values():
                mm.close()

            self.regions = new_regions
            self.tags = new_tags

        print(f"[shm-service] Loaded {len(self.tags)} tags")

    # ---------------------------
    # IPC
    # ---------------------------

    def _open_socket(self):
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o660)
        self.sock.listen(5)

        print(f"[shm-service] Listening on {SOCKET_PATH}")

    def _serve_forever(self):
        while True:
            conn, _ = self.sock.accept()
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket):
        try:
            data = conn.recv(8192)
            if not data:
                return

            request = json.loads(data.decode())
            response = self._handle_request(request)
            conn.sendall(json.dumps(response).encode())

        except Exception as e:
            conn.sendall(json.dumps({"error": str(e)}).encode())
        finally:
            conn.close()

    # ---------------------------
    # Request Handling
    # ---------------------------

    def _handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        if "read" in req:
            return {"read": self._read_tags(req["read"])}

        if "write" in req:
            self._write_tags(req["write"])
            return {"status": "ok"}

        if "reload" in req:
            self._load_tags()
            return {"status": "reloaded"}

        raise ValueError("Unknown command")

    # ---------------------------
    # Read / Write
    # ---------------------------

    def _read_tags(self, names):
        result = {}

        with self.lock:
            for name in names:
                tag = self.tags[name]
                mm = self.regions[tag.region]

                raw = mm[tag.offset : tag.offset + tag.size]
                value = struct.unpack(tag.struct_fmt, raw)[0]

                if tag.scale:
                    value *= tag.scale

                result[name] = value

        return result

    def _write_tags(self, values: Dict[str, Any]):
        with self.lock:
            for name, value in values.items():
                tag = self.tags[name]
                mm = self.regions[tag.region]

                if tag.scale:
                    value = value / tag.scale

                packed = struct.pack(tag.struct_fmt, value)
                mm[tag.offset : tag.offset + tag.size] = packed


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    tags_file = os.environ.get("RASPIPLC_TAGS_FILE", DEFAULT_TAGS_FILE)

    svc = SHMService(tags_file)
    svc.start()


if __name__ == "__main__":
    main()

