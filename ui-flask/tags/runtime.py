# tags/runtime.py
from flask_socketio import Namespace
from tags.state import (
    get_tag_updates,
    subscribe_tags,
    unsubscribe_tags,
)
from tags.registry import TAGS
from tags.usb_comm import UsbComm

NAMESPACE = "/tags"

_poller = None

def set_poller(poller):
    global _poller
    _poller = poller


class TagNamespace(Namespace):

    def on_connect(self):
        print("[tags] client connected")

    def on_disconnect(self):
        print("[tags] client disconnected")

    def on_subscribe(self, msg):
        tags = msg.get("tags", [])
        subscribe_tags(tags)

    def on_unsubscribe(self, msg):
        tags = msg.get("tags", [])
        unsubscribe_tags(tags)

    # ✅ WRITE HANDLER LIVES HERE
    def on_tag_write(self, msg):
        tag = msg.get("tag")
        value = msg.get("value")

        td = TAGS.get(tag)
        if not td or not td.write_cmd:
            return {"status": "error", "msg": "Tag not writable"}

        if not _poller:
            return {"status": "error", "msg": "Poller not ready"}

        payload = td.writer(value)

        try:
            _poller.enqueue_write(
                td.object_id,
                td.write_cmd,
                payload
            )
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "msg": str(e)}


def register_tag_namespace(socketio):
    socketio.on_namespace(TagNamespace(NAMESPACE))


def emit_tag_updates(socketio):
    updates = get_tag_updates()
    if updates:
        socketio.emit("tag_update", updates, namespace=NAMESPACE)
