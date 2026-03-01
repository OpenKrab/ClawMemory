from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Commitment:
    id: str
    text: str
    due_at: str
    status: str
    created_at: str
    updated_at: str
    session_id: str | None
    metadata: dict[str, Any]
    completed_at: str | None
    note: str | None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    src = dt or _now_utc()
    if src.tzinfo is None:
        src = src.replace(tzinfo=timezone.utc)
    return src.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CommitmentEngine:
    def __init__(self, root: str | Path = "memory") -> None:
        self.root = Path(root)
        self.db_path = self.root / "commitments.sqlite3"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS commitments (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    session_id TEXT,
                    metadata_json TEXT NOT NULL,
                    completed_at TEXT,
                    note TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_commitments_status_due ON commitments(status, due_at)"
            )

    def create(
        self,
        text: str,
        due_in_seconds: int | None = None,
        due_at: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text is required")

        if due_at:
            due_dt = _parse_iso(due_at)
        else:
            seconds = max(1, int(due_in_seconds or 300))
            due_dt = _now_utc() + timedelta(seconds=seconds)

        cid = str(uuid4())
        now = _iso()
        row = Commitment(
            id=cid,
            text=clean_text,
            due_at=_iso(due_dt),
            status="pending",
            created_at=now,
            updated_at=now,
            session_id=session_id,
            metadata=metadata or {},
            completed_at=None,
            note=None,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO commitments (
                    id, text, due_at, status, created_at, updated_at,
                    session_id, metadata_json, completed_at, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.id,
                    row.text,
                    row.due_at,
                    row.status,
                    row.created_at,
                    row.updated_at,
                    row.session_id,
                    json.dumps(row.metadata, ensure_ascii=True),
                    row.completed_at,
                    row.note,
                ),
            )

        return self.get(cid) or {"id": cid}

    def _row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "text": row[1],
            "due_at": row[2],
            "status": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "session_id": row[6],
            "metadata": json.loads(row[7]),
            "completed_at": row[8],
            "note": row[9],
        }

    def get(self, commitment_id: str) -> dict[str, Any] | None:
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, text, due_at, status, created_at, updated_at,
                       session_id, metadata_json, completed_at, note
                FROM commitments
                WHERE id = ?
                """,
                (commitment_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list(self, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        self.initialize()
        lim = max(1, min(int(limit), 5000))
        with sqlite3.connect(self.db_path) as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT id, text, due_at, status, created_at, updated_at,
                           session_id, metadata_json, completed_at, note
                    FROM commitments
                    WHERE status = ?
                    ORDER BY due_at ASC
                    LIMIT ?
                    """,
                    (status, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, text, due_at, status, created_at, updated_at,
                           session_id, metadata_json, completed_at, note
                    FROM commitments
                    ORDER BY
                        CASE status
                            WHEN 'overdue' THEN 0
                            WHEN 'pending' THEN 1
                            ELSE 2
                        END,
                        due_at ASC
                    LIMIT ?
                    """,
                    (lim,),
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def complete(self, commitment_id: str, note: str | None = None) -> dict[str, Any] | None:
        self.initialize()
        now = _iso()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                UPDATE commitments
                SET status = 'completed', updated_at = ?, completed_at = ?, note = ?
                WHERE id = ? AND status != 'completed'
                """,
                (now, now, note, commitment_id),
            )
            if cur.rowcount <= 0:
                return self.get(commitment_id)
        return self.get(commitment_id)

    def snooze(self, commitment_id: str, seconds: int) -> dict[str, Any] | None:
        self.initialize()
        row = self.get(commitment_id)
        if not row:
            return None
        due = _parse_iso(row["due_at"]) + timedelta(seconds=max(1, int(seconds)))
        now = _iso()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE commitments
                SET due_at = ?, updated_at = ?, status = CASE WHEN status='completed' THEN status ELSE 'pending' END
                WHERE id = ?
                """,
                (_iso(due), now, commitment_id),
            )
        return self.get(commitment_id)

    def poll_due(self, limit: int = 50) -> dict[str, Any]:
        self.initialize()
        now = _iso()
        lim = max(1, min(int(limit), 1000))
        with sqlite3.connect(self.db_path) as conn:
            due_rows = conn.execute(
                """
                SELECT id
                FROM commitments
                WHERE status = 'pending' AND due_at <= ?
                ORDER BY due_at ASC
                LIMIT ?
                """,
                (now, lim),
            ).fetchall()

            ids = [r[0] for r in due_rows]
            if ids:
                conn.executemany(
                    "UPDATE commitments SET status='overdue', updated_at=? WHERE id=?",
                    [(now, cid) for cid in ids],
                )

        items = [self.get(cid) for cid in ids]
        return {
            "status": "ok",
            "now": now,
            "count": len(ids),
            "due": [item for item in items if item is not None],
        }

    def next_wakeup_seconds(self) -> float | None:
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT due_at FROM commitments WHERE status='pending' ORDER BY due_at ASC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        delta = (_parse_iso(row[0]) - _now_utc()).total_seconds()
        return max(0.0, delta)

    def health(self) -> dict[str, Any]:
        self.initialize()
        now = _iso()
        with sqlite3.connect(self.db_path) as conn:
            counts = dict(
                conn.execute(
                    "SELECT status, COUNT(*) FROM commitments GROUP BY status"
                ).fetchall()
            )
            due_soon = conn.execute(
                """
                SELECT COUNT(*) FROM commitments
                WHERE status='pending' AND due_at <= ?
                """,
                (_iso(_now_utc() + timedelta(minutes=5)),),
            ).fetchone()[0]
        return {
            "counts": {
                "pending": int(counts.get("pending", 0)),
                "overdue": int(counts.get("overdue", 0)),
                "completed": int(counts.get("completed", 0)),
            },
            "due_soon_5m": int(due_soon),
            "now": now,
        }

    def watch(
        self,
        interval_seconds: float = 1.0,
        max_sleep_seconds: float = 30.0,
        emit: callable | None = None,
    ) -> None:
        """Run in-process scheduler loop.

        This is an event-loop style watcher: it sleeps until next due item (bounded by max_sleep_seconds),
        then polls and emits due items.
        """
        base_sleep = max(0.1, interval_seconds)
        max_sleep = max(base_sleep, max_sleep_seconds)
        out = emit or print

        while True:
            polled = self.poll_due(limit=200)
            if polled["count"] > 0:
                out(json.dumps(polled, ensure_ascii=True))

            next_due = self.next_wakeup_seconds()
            if next_due is None:
                time.sleep(max_sleep)
                continue

            sleep_for = min(max_sleep, max(base_sleep, next_due))
            time.sleep(sleep_for)
