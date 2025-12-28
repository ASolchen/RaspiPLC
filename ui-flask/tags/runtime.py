from flask_socketio import Namespace
from flask import request
import time
import socket
import json

DEFAULT_UPDATE_RATE_MS = 200
SHM_SOCKET_PATH = "/run/raspiplc-shm.sock"

# Per-client subscription registry
_clients = {}


# ---------------------------------------------------------------------------
# SHM client helpers
# ---------------------------------------------------------------------------

def shm_read_tags(tag_names):
    """
    Read tags from shm-service.
    Returns dict {tag: value}
    """
    if not tag_names:
        return {}

    req = {"read": list(tag_names)}

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(SHM_SOCKET_PATH)
        sock.sendall(json.dumps(req).encode())
        data = sock.recv(8192)

    if not data:
        raise RuntimeError("No response from shm-service")

    resp = json.loads(data.decode())

    if "error" in resp:
        raise RuntimeError(resp["error"])

    return resp.get("read", {})


def shm_write_tags(values):
    """
    Write tags to shm-service.
    values: dict {tag: value}
    """
    if not values:
        return

    req = {"write": values}

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(SHM_SOCKET_PATH)
        sock.sendall(json.dumps(req).encode())
        data = sock.recv(8192)

    if not data:
        raise RuntimeError("No response from shm-service")

    resp = json.loads(data.decode())

    if "error" in resp:
        raise RuntimeError(resp["error"])


# ---------------------------------------------------------------------------
# Socket.IO Namespace
# ---------------------------------------------------------------------------

class TagNamespace(Namespace):
    def on_connect(self):
        sid = request.sid
        _clients[sid] = {
            "tags": set(),
            "rate_ms": DEFAULT_UPDATE_RATE_MS,
            "last_emit": 0,
        }
        print(f"[tags] client connected: {sid}")

    def on_disconnect(self):
        sid = request.sid
        _clients.pop(sid, None)
        print(f"[tags] client disconnected: {sid}")

    def on_subscribe(self, data):
        sid = request.sid

        tags = data.get("tags", [])
        rate_ms = data.get("rate_ms", DEFAULT_UPDATE_RATE_MS)

        _clients[sid]["tags"] = set(tags)
        _clients[sid]["rate_ms"] = rate_ms

        print(
            f"[tags] subscribe sid={sid} "
            f"tags={_clients[sid]['tags']} "
            f"rate_ms={rate_ms}"
        )

    def on_tag_write(self, data):
        """
        Handle write requests from the UI.
        Expected format:
          { "tag": "heater.1.pct", "value": 45 }
        or
          { "values": { "tag1": v1, "tag2": v2 } }
        """
        try:
            if "values" in data:
                shm_write_tags(data["values"])
            elif "tag" in data and "value" in data:
                shm_write_tags({data["tag"]: data["value"]})
            else:
                raise ValueError("Invalid write payload")

            print(f"[tags] write OK: {data}")

        except Exception as e:
            print(f"[tags] write ERROR: {e}")


# ---------------------------------------------------------------------------
# Background update loop
# ---------------------------------------------------------------------------

def emit_tag_updates(socketio):
    """
    Called periodically by a background thread.
    Reads live tag values from shm-service and emits to clients.
    """
    now = time.time() * 1000

    for sid, state in list(_clients.items()):
        if now - state["last_emit"] < state["rate_ms"]:
            continue

        state["last_emit"] = now

        if not state["tags"]:
            continue

        try:
            values = shm_read_tags(state["tags"])
        except Exception as e:
            print(f"[tags] SHM read error: {e}")
            continue

        if values:
            socketio.emit(
                "tag_update",
                {"tags": values, "ts": time.time()},
                namespace="/tags",
                room=sid,
            )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_tag_namespace(socketio):
    socketio.on_namespace(TagNamespace("/tags"))
