from flask_socketio import Namespace, emit
import time

DEFAULT_UPDATE_RATE_MS = 200


class TagNamespace(Namespace):
    def __init__(self, namespace):
        super().__init__(namespace)
        self.subscribed_tags = set()
        self.rate_ms = DEFAULT_UPDATE_RATE_MS
        self.last_emit = 0

    def on_connect(self):
        print("[tags] client connected")

    def on_disconnect(self):
        print("[tags] client disconnected")

    def on_subscribe(self, data):
        """
        Expected payload:
        {
            tags: ["tag.a", "tag.b"],
            rate_ms: 500   # optional
        }
        """
        tags = data.get("tags", [])
        if isinstance(tags, list):
            self.subscribed_tags = set(tags)
        else:
            self.subscribed_tags = set()

        self.rate_ms = data.get("rate_ms", DEFAULT_UPDATE_RATE_MS)

        print(
            f"[tags] subscribe tags={self.subscribed_tags} "
            f"rate_ms={self.rate_ms}"
        )

    def maybe_emit(self, all_tags):
        """
        Emit filtered tag updates based on subscription and rate.
        Called by the mock source.
        """
        now = time.time() * 1000
        if now - self.last_emit < self.rate_ms:
            return

        self.last_emit = now

        if self.subscribed_tags:
            filtered = {
                k: v for k, v in all_tags.items()
                if k in self.subscribed_tags
            }
        else:
            filtered = all_tags

        emit(
            "tag_update",
            {
                "tags": filtered,
                "ts": time.time()
            },
            namespace="/tags"
        )

    def on_tag_write(self, data):
        print("[tags] write request:", data)
        # Later: validate + write to SHM


# ---- registry so mock source can access active namespaces ----

_active_namespaces = []


def register_tag_namespace(socketio):
    ns = TagNamespace("/tags")
    socketio.on_namespace(ns)
    _active_namespaces.append(ns)


def get_active_namespaces():
    return list(_active_namespaces)

