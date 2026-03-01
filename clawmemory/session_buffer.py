from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .autocapture import CaptureConfig, extract_reusable_facts
from .store import MemoryStore


class SessionBuffer:
    def __init__(self, root: str | Path = "memory") -> None:
        self.root = Path(root)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _buffer_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.jsonl"

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        source: str = "session/buffer",
        auto_flush_max_turns: int = 24,
        min_confidence: float = 0.7,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_id": session_id,
            "role": role,
            "content": content.strip(),
            "source": source,
        }

        if not entry["content"]:
            return {"status": "ignored", "reason": "empty-content"}

        buffer_path = self._buffer_path(session_id)
        with buffer_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")

        turns = self.read_turns(session_id)
        out: dict[str, Any] = {
            "status": "buffered",
            "session_id": session_id,
            "turns_in_buffer": len(turns),
            "path": str(buffer_path),
        }

        if auto_flush_max_turns > 0 and len(turns) >= auto_flush_max_turns:
            out["auto_flush"] = self.flush_session(
                session_id=session_id,
                min_confidence=min_confidence,
                keep_buffer=False,
            )

        return out

    def read_turns(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        buffer_path = self._buffer_path(session_id)
        if not buffer_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        for line in buffer_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

        if limit is None:
            return rows
        return rows[-limit:]

    def flush_session(
        self,
        session_id: str,
        min_confidence: float = 0.7,
        keep_buffer: bool = False,
    ) -> dict[str, Any]:
        turns = self.read_turns(session_id)
        if not turns:
            return {"status": "empty", "session_id": session_id, "writes": []}

        conversation = [{"role": t["role"], "content": t["content"]} for t in turns]
        extracted = extract_reusable_facts(
            conversation=conversation,
            config=CaptureConfig(min_confidence=min_confidence),
            source=f"session/{session_id}",
        )

        store = MemoryStore(self.root)
        writes = []
        for item in extracted:
            item.setdefault("metadata", {})
            item["metadata"]["session_id"] = session_id
            writes.append(store.write(item))

        if not keep_buffer:
            self._buffer_path(session_id).unlink(missing_ok=True)

        return {
            "status": "flushed",
            "session_id": session_id,
            "turn_count": len(turns),
            "extracted_count": len(extracted),
            "writes": writes,
            "buffer_cleared": not keep_buffer,
        }
