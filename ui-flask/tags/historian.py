"""
Historian manager.

- Starts in Null mode
- Periodically probes QuestDB ILP port (9009)
- Attaches QuestDB historian when available
- Detaches if QuestDB goes away
- Flask/runtime code never cares which backend is active
"""

import socket
import threading
import time

from tags.historian_null import NullHistorian

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QUESTDB_HOST = "127.0.0.1"
QUESTDB_PORT = 9009
RETRY_INTERVAL_SEC = 5.0
SOCKET_TIMEOUT_SEC = 0.25

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _questdb_available() -> bool:
    """
    Lightweight TCP probe for QuestDB ILP port.
    """
    try:
        with socket.create_connection(
            (QUESTDB_HOST, QUESTDB_PORT),
            timeout=SOCKET_TIMEOUT_SEC,
        ):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Historian Manager
# ---------------------------------------------------------------------------


class HistorianManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._backend = NullHistorian()
        self._backend_name = "null"
        self._stop_evt = threading.Event()

        print("[Historian] Starting in NULL mode")

        # Background attach / health thread
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="HistorianMonitor",
            daemon=True,
        )
        self._thread.start()

    # ------------------------
    # Public API (proxy)
    # ------------------------

    def record(self, tag: str, value, quality="good"):
        """
        Record a tag value (non-blocking).
        Always safe to call.
        """
        with self._lock:
            self._backend.record(tag, value, quality)

    def query(self, *args, **kwargs):
        """
        Query historical data.
        """
        with self._lock:
            return self._backend.query(*args, **kwargs)

    # ------------------------
    # Backend management
    # ------------------------

    def _attach_questdb(self):
        try:
            from tags.historian_questdb import QuestDBHistorian

            backend = QuestDBHistorian()
            self._backend = backend
            self._backend_name = "questdb"

            print("[Historian] QuestDB attached (ILP 9009)")
        except Exception as e:
            print(f"[Historian] QuestDB attach failed: {e}")
            self._backend = NullHistorian()
            self._backend_name = "null"

    def _detach_backend(self):
        print("[Historian] QuestDB disconnected, falling back to NULL")
        self._backend = NullHistorian()
        self._backend_name = "null"

    # ------------------------
    # Monitor loop
    # ------------------------

    def _monitor_loop(self):
        """
        Periodically check QuestDB availability and attach/detach as needed.
        """
        while not self._stop_evt.is_set():
            try:
                available = _questdb_available()

                with self._lock:
                    if available and self._backend_name == "null":
                        self._attach_questdb()

                    elif not available and self._backend_name == "questdb":
                        self._detach_backend()

            except Exception as e:
                # Never let historian monitoring kill the app
                print(f"[Historian] Monitor error: {e}")

            time.sleep(RETRY_INTERVAL_SEC)

    # ------------------------
    # Shutdown (optional)
    # ------------------------

    def stop(self):
        self._stop_evt.set()
        self._thread.join(timeout=1.0)


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_historian_mgr: HistorianManager | None = None


def get_historian() -> HistorianManager:
    global _historian_mgr
    if _historian_mgr is None:
        _historian_mgr = HistorianManager()
    return _historian_mgr
