from flask import Flask
from flask_socketio import SocketIO
from threading import Thread
import time

from tags.poller import Poller
from tags.usb_comm import UsbComm
from web.routes import register_routes
from tags.runtime import register_tag_namespace, emit_tag_updates

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
app.config["SECRET_KEY"] = "dev"

socketio = SocketIO(app, async_mode="threading")
# ---------------- Hardware poller ----------------
usb = UsbComm("COM8", 500000)
poller = Poller(usb)
from tags.runtime import set_poller
set_poller(poller)

def start_tag_update_loop():
    """
    Background thread that periodically emits tag updates
    using shm-service as the data source.
    """
    def run():
        while True:
            emit_tag_updates(socketio)
            time.sleep(0.05)  # 50 ms tick; per-client rate_ms still applies

    socketio.start_background_task(run)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

register_routes(app)
register_tag_namespace(socketio)
socketio.start_background_task(poller.run)
start_tag_update_loop()

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True,
    )
