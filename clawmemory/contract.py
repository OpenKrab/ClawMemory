from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class MemoryEntry:
    """Normalized memory record used across markdown and index layers."""

    text: str
    source: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["confidence"] = float(max(0.0, min(1.0, self.confidence)))
        out["tags"] = sorted({t.strip().lower() for t in self.tags if t and t.strip()})
        out["text"] = self.text.strip()
        out["source"] = self.source.strip()
        return out

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MemoryEntry":
        missing = [k for k in ("text", "source") if not payload.get(k)]
        if missing:
            raise ValueError(f"Missing required payload fields: {', '.join(missing)}")
        return cls(
            text=str(payload["text"]),
            source=str(payload["source"]),
            tags=list(payload.get("tags", [])),
            confidence=float(payload.get("confidence", 1.0)),
            metadata=dict(payload.get("metadata", {})),
        )
