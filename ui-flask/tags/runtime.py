from flask_socketio import Namespace
from flask import request
import time

DEFAULT_UPDATE_RATE_MS = 200

# Per-client subscription registry
_clients = {}


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
        print("[tags] write request:", data)
        # Later: validate + write to SHM


def emit_tag_updates(socketio, all_tags):
    """
    Called by background thread.
    """
    now = time.time() * 1000

    for sid, state in list(_clients.items()):
        if now - state["last_emit"] < state["rate_ms"]:
            continue

        state["last_emit"] = now

        if state["tags"]:
            filtered = {
                k: v for k, v in all_tags.items()
                if k in state["tags"]
            }
        else:
            # TEMPORARY: empty list = nothing (safer default)
            filtered = {}

        if filtered:
            socketio.emit(
                "tag_update",
                {"tags": filtered, "ts": time.time()},
                namespace="/tags",
                room=sid,
            )


def register_tag_namespace(socketio):
    socketio.on_namespace(TagNamespace("/tags"))
