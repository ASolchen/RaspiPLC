# tags/historian_questdb.py

from questdb.ingress import Sender
import socket
import time


class QuestDBHistorian:
    def __init__(self, host="127.0.0.1", port=9009):
        self.host = host
        self.port = port
        self.sender = Sender(host=host, port=port)
        print("[Historian] QuestDB connected")

    def handle_tag_updates(self, updates: dict):
        ts_ns = int(time.time() * 1e9)

        for tag, value in updates.items():
            self.sender.row(
                "tag_history",
                symbols={"tag": tag},
                columns={"value": float(value)},
                at=ts_ns
            )

        self.sender.flush()

    def query_history(self, *args, **kwargs):
        # Optional later via HTTP SQL
        return []
