# tags/historian_questdb.py

import time
import logging
import requests
import logging

log = logging.getLogger(__name__)
from questdb.ingress import Sender, Protocol


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
        self.sender = Sender(
            Protocol.Tcp,
            host,
            port,
        )
        self.closed = False

        log.info(f"[Historian] QuestDB historian connected ({host}:{port})")

    # ------------------------------------------------------------------
    # Public API (matches HistorianManager expectations)
    # ------------------------------------------------------------------

    def record(self, tag: str, value, quality="good"):
        """
        Record a single tag sample.

        Raises on failure so the manager can detach.
        """
        if self.closed:
            raise RuntimeError("Sender is closed")  
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

    def query(
        self,
        tags,
        after_ts: int = 0,
        limit: int = 1000,
    ):
        """
        Query historical tag data from QuestDB via HTTP SQL.

        Returns rows in the format:
        {
            "ts": <int ns>,
            "tag": <str>,
            "value": <float>,
            "quality": <str>
        }
        """

        if not tags:
            return []

        # Build IN ('tag1','tag2',...)
        tag_list = ",".join(f"'{t}'" for t in tags)

        sql = f"""
            SELECT
                ts,
                tag,
                value,
                quality
            FROM tag_history
            WHERE tag IN ({tag_list})
              AND ts > {int(after_ts)}
            ORDER BY ts
            LIMIT {int(limit)}
        """

        url = f"http://{self.host}:9000/exec"

        try:
            resp = requests.get(
                url,
                params={"query": sql},
                timeout=2,
            )
            resp.raise_for_status()
            payload = resp.json()

        except Exception as e:
            log.warning("[QuestDB] query failed: %s", e)
            return []

        # QuestDB returns column-oriented JSON
        columns = payload.get("columns", [])
        dataset = payload.get("dataset", [])

        if not columns or not dataset:
            return []

        col_idx = {col["name"]: i for i, col in enumerate(columns)}

        rows = []
        for row in dataset:
            try:
                rows.append(
                    {
                        "ts": row[col_idx["ts"]],
                        "tag": row[col_idx["tag"]],
                        "value": row[col_idx["value"]],
                        "quality": row[col_idx.get("quality", -1)]
                        if "quality" in col_idx
                        else None,
                    }
                )
            except Exception as e:
                log.debug("[QuestDB] bad row skipped: %s (%s)", row, e)

        return rows
