import time
import random
from threading import Thread


def start_mock_source(socketio):
    def run():
        while True:
            payload = {
                "tags": {
                    "smoker.temp": round(200 + random.random() * 10, 1),
                    "meat.temp": round(145 + random.random() * 5, 1),
                    "heater.1.pct": round(random.random() * 100, 1),
                },
                "ts": time.time(),
            }

            socketio.emit("tag_update", payload, namespace="/tags")
            time.sleep(1)

    thread = Thread(target=run, daemon=True)
    thread.start()
