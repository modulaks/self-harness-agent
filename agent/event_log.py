"""Append-only event log (SQLite). Brak UPDATE/DELETE z założenia.
W M4 zamiana backendu na Postgres przy zachowaniu tego interfejsu."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  run_id TEXT NOT NULL,
  harness_version TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


class EventLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def append(self, run_id: str, harness_version: str, kind: str, payload: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO events (ts, run_id, harness_version, kind, payload) VALUES (?,?,?,?,?)",
            (time.time(), run_id, harness_version, kind, json.dumps(payload, ensure_ascii=False, default=str)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def _rows(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        cur = self.conn.execute(sql, args)
        cols = [c[0] for c in cur.description]
        out = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d["payload"] = json.loads(d["payload"])
            out.append(d)
        return out

    def run_events(self, run_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,))

    def by_kind(self, kind: str, since_id: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT * FROM events WHERE kind=? AND id>? ORDER BY id LIMIT ?", (kind, since_id, limit)
        )

    def count(self, kind: str | None = None) -> int:
        if kind:
            return self.conn.execute("SELECT COUNT(*) FROM events WHERE kind=?", (kind,)).fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def last_id(self) -> int:
        row = self.conn.execute("SELECT MAX(id) FROM events").fetchone()
        return int(row[0] or 0)

    def close(self) -> None:
        self.conn.close()
