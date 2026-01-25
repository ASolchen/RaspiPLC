# tags/historian_null.py

class NullHistorian:
    """
    No-op historian backend.

    Safe default when no real historian is available.
    """

    def record(self, tag: str, value, quality="good"):
        # Intentionally do nothing
        return

    def query(self, *args, **kwargs):
        # No history available
        return []

    def close(self):
        # Optional cleanup hook
        return
