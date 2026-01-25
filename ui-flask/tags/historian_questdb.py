# tags/historian_questdb.py

import time
from questdb.ingress import Sender


class QuestDBHistorian:
    """
    QuestDB historian backend using ILP over TCP (port 9009).

    This class is intentionally thin:
    - no retry logic
    - no attach/detach logic
    - raises on failure so HistorianManager can react
    """

    def __init__(self, host="127.0.0.1", port=9009):
        self.host = host
        self.port = port
        self.sender = Sender(host=host, port=port)

        print(f"[Historian] QuestDB historian connected ({host}:{port})")

    # ------------------------------------------------------------------
    # Public API (matches HistorianManager expectations)
    # ------------------------------------------------------------------

    def record(self, tag: str, value, quality="good"):
        """
        Record a single tag sample.

        Raises on failure so the manager can detach.
        """
        ts_ns = time.time_ns()

        try:
            self.sender.row(
                "tag_history",
                symbols={
                    "tag": tag,
                    "quality": str(quality),
                },
                columns={
                    "value": float(value),
                },
                at=ts_ns,
            )
            self.sender.flush()

        except Exception:
            # Let the manager handle fallback
            raise

    def query(self, *args, **kwargs):
        """
        Historical query via QuestDB HTTP SQL (future).

        For now, return empty and let REST layer handle it.
        """
        return []

    # ------------------------------------------------------------------
    # Optional cleanup hook
    # ------------------------------------------------------------------

    def close(self):
        try:
            self.sender.close()
        except Exception:
            pass
