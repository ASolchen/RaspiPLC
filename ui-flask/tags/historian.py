# tags/historian.py

import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path("data/tag_history.sqlite")

HISTORIAN_TAGS = {
    "tic1.sp",
    "tic1.pid.pv",
    "tic1.pid.cv",
    "tic1.tc.mode",
}

DEFAULT_QUALITY = "good"


# ---------------------------------------------------------------------------
# Historian class
# ---------------------------------------------------------------------------

class TagHistorian:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = None

        self._open_db()
        self._init_schema()

    # ---------------------------------------------------------------------

    def _open_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")

    # ---------------------------------------------------------------------

    def _init_schema(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_history (
                    ts      INTEGER NOT NULL,
                    tag     TEXT    NOT NULL,
                    value   REAL,
                    quality TEXT    NOT NULL
                )
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_history_ts
                    ON tag_history(ts)
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_history_tag_ts
                    ON tag_history(tag, ts)
            """)

    # ---------------------------------------------------------------------
    # WRITE PATH (called by runtime)
    # ---------------------------------------------------------------------

    def handle_tag_updates(self, updates: dict):
        if not updates:
            return

        ts = int(time.time() * 1000)

        rows = [
            (ts, tag, float(value), DEFAULT_QUALITY)
            for tag, value in updates.items()
            if tag in HISTORIAN_TAGS
        ]

        if not rows:
            return

        with self._lock:
            self._conn.executemany(
                "INSERT INTO tag_history (ts, tag, value, quality) "
                "VALUES (?, ?, ?, ?)",
                rows
            )
            self._conn.commit()

    # ---------------------------------------------------------------------
    # READ PATH (used by REST API)
    # ---------------------------------------------------------------------

    def query_history(
        self,
        tags: List[str],
        start_ts: int,
        end_ts: int,
        limit: Optional[int] = None
    ) -> List[dict]:

        if not tags:
            return []

        placeholders = ",".join("?" for _ in tags)

        sql = f"""
            SELECT ts, tag, value, quality
            FROM tag_history
            WHERE tag IN ({placeholders})
              AND ts > ?
              AND ts <= ?
            ORDER BY ts ASC
        """

        params = list(tags) + [start_ts, end_ts]

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        cur = self._conn.execute(sql, params)
        rows = cur.fetchall()

        return [
            {
                "ts": row[0],
                "tag": row[1],
                "value": row[2],
                "quality": row[3]
            }
            for row in rows
        ]

    # ---------------------------------------------------------------------

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_historian = None

def get_historian() -> TagHistorian:
    global _historian
    if _historian is None:
        _historian = TagHistorian()
    return _historian
