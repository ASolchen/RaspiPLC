import time
import random
from threading import Thread
from .runtime import get_active_namespaces


def start_mock_source():
    def run():
        while True:
            all_tags = {
                "smoker.temp": round(200 + random.random() * 10, 1),
                "meat.temp": round(145 + random.random() * 5, 1),
                "heater.1.pct": round(random.random() * 100, 1),
            }

            for ns in get_active_namespaces():
                ns.maybe_emit(all_tags)

            time.sleep(0.1)

    thread = Thread(target=run, daemon=True)
    thread.start()
