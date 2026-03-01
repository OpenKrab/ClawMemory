from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

FACT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(i prefer|i like|i usually|my preference is)\b", "preference"),
    (r"\b(deadline|due|by\s+\d{4}-\d{2}-\d{2})\b", "constraint"),
    (r"\b(currently working on|ongoing|in progress|next step)\b", "ongoing_task"),
    (r"\b(do not|don't|never)\b", "constraint"),
]


@dataclass(slots=True)
class CaptureConfig:
    min_confidence: float = 0.7


def _score_fact(text: str) -> float:
    lower = text.lower().strip()
    if len(lower) < 15:
        return 0.2
    signal = 0.4
    for pattern, _ in FACT_PATTERNS:
        if re.search(pattern, lower):
            signal += 0.2
    if any(ch.isdigit() for ch in lower):
        signal += 0.1
    if len(lower.split()) > 8:
        signal += 0.1
    return max(0.0, min(1.0, signal))


def extract_reusable_facts(
    conversation: list[dict[str, Any]],
    config: CaptureConfig | None = None,
    source: str = "autocapture/conversation",
) -> list[dict[str, Any]]:
    cfg = config or CaptureConfig()
    extracted: list[dict[str, Any]] = []

    for turn in conversation:
        role = str(turn.get("role", "")).lower()
        content = str(turn.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue

        score = _score_fact(content)
        if score < cfg.min_confidence:
            continue

        tags = ["autocapture", role]
        for pattern, tag in FACT_PATTERNS:
            if re.search(pattern, content.lower()):
                tags.append(tag)

        extracted.append(
            {
                "text": content,
                "source": source,
                "tags": sorted(set(tags)),
                "confidence": round(score, 3),
                "metadata": {"role": role},
            }
        )

    return extracted
