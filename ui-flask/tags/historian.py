# tags/historian.py
"""
Historian factory.

Selects a historian backend at runtime:
- QuestDB if reachable on localhost
- Otherwise a Null historian (no-op)

The rest of the application MUST only call get_historian().
"""

import socket

from tags.historian_null import NullHistorian

# Singleton instance
_historian = None


def _questdb_available(host="127.0.0.1", port=9009, timeout=0.25) -> bool:
    """
    Check whether QuestDB ILP port is reachable.
    This is intentionally lightweight and non-fatal.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_historian():
    """
    Return the active historian instance.
    Decision is made once and cached.
    """
    global _historian

    if _historian is not None:
        return _historian

    # Try QuestDB first
    if _questdb_available():
        try:
            from tags.historian_questdb import QuestDBHistorian

            _historian = QuestDBHistorian()
            print("[Historian] Using QuestDB")
            return _historian

        except Exception as e:
            # QuestDB exists but failed to init
            print(f"[Historian] QuestDB init failed: {e}")

    # Fallback: no-op historian
    print("[Historian] Disabled (QuestDB not available)")
    _historian = NullHistorian()
    return _historian
