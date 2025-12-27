import time
import random
from threading import Thread
from .runtime import emit_tag_updates


def start_mock_source(socketio):
    def run():
        while True:
            all_tags = {
                "smoker.temp": round(200 + random.random() * 10, 1),
                "meat.temp": round(145 + random.random() * 5, 1),
                "heater.1.pct": round(random.random() * 100, 1),
            }

            emit_tag_updates(socketio, all_tags)
            time.sleep(0.1)

    Thread(target=run, daemon=True).start()
