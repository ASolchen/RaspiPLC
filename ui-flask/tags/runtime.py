from flask_socketio import Namespace, emit
from .mock_source import start_mock_source


class TagNamespace(Namespace):
    def on_connect(self):
        print("[tags] client connected")

    def on_disconnect(self):
        print("[tags] client disconnected")

    def on_subscribe(self, data):
        print("[tags] subscribe:", data)
        emit("subscribed", {"status": "ok"})

    def on_tag_write(self, data):
        print("[tags] write request:", data)
        # For now: just log it
        # Later: validate, write to SHM, confirm


def register_tag_namespace(socketio):
    ns = TagNamespace("/tags")
    socketio.on_namespace(ns)

    # Start mock data source AFTER socketio exists
    start_mock_source(socketio)
