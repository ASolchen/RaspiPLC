"""
Historian manager.

- Starts in Null mode
- Periodically probes QuestDB ILP port (9009)
- Attaches QuestDB historian when available
- Detaches if QuestDB goes away
- Flask/runtime code never cares which backend is active
"""

import platform
import socket
import threading
import time
import logging
log = logging.getLogger(__name__)

from tags.historian_null import NullHistorian

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QUESTDB_HOST = "127.0.0.1"
if platform.system() == "Windows":
    QUESTDB_HOST = "smoker.lan"
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

        log.info("[Historian] Starting in NULL mode")

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
    
    def handle_tag_updates(self, updates: dict):
        """
        Backwards-compatible handler for legacy callers.

        Expects: { tag_name: value }
        """
        for tag, value in updates.items():
            try:
                self.record(tag, value)
            except Exception:
                # Never let historian failures break runtime
                pass

    def query(self, *args, **kwargs):
        """
        Query historical data.
        """
        with self._lock:
            return self._backend.query(*args, **kwargs)
    
    def query_history(self, *args, **kwargs):
        """
        Backwards-compatible alias for legacy callers.
        """
        return self.query(*args, **kwargs)


    # ------------------------
    # Backend management
    # ------------------------

    def _attach_questdb(self):
        try:
            import inspect
            from tags.historian_questdb import QuestDBHistorian
            log.info("QuestDBHistorian loaded from %s", inspect.getfile(QuestDBHistorian))
            log.info("QuestDBHistorian signature: %s", inspect.signature(QuestDBHistorian))

            backend = QuestDBHistorian(QUESTDB_HOST, QUESTDB_PORT)
            self._backend = backend
            self._backend_name = "questdb"

            log.info("[Historian] QuestDB attached (ILP 9009)")
        except Exception as e:
            log.info(f"[Historian] QuestDB attach failed: {e}")
            self._backend = NullHistorian()
            self._backend_name = "null"

    def _detach_backend(self):
        log.info("[Historian] QuestDB disconnected, falling back to NULL")
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
                log.info(f"[Historian] Monitor error: {e}")

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
