from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .commitments import CommitmentEngine
from .store import MemoryStore


@dataclass(slots=True)
class ReceiptEvent:
    merchant: str
    amount: float
    timestamp: str


def _month_day(ts: str) -> int:
    try:
        return datetime.fromisoformat(ts).day
    except ValueError:
        return 15


def capture_receipt_patterns(
    events: list[dict[str, Any]],
    root: str = "memory",
    source: str = "clawreceipt/patterns",
) -> dict[str, Any]:
    store = MemoryStore(root)
    parsed = [ReceiptEvent(str(e.get("merchant", "")).strip(), float(e.get("amount", 0.0)), str(e.get("timestamp", ""))) for e in events]
    parsed = [p for p in parsed if p.merchant]
    if not parsed:
        return {"status": "no_data", "writes": []}

    merchant_counts = Counter(p.merchant.lower() for p in parsed)
    writes: list[dict[str, Any]] = []

    for merchant, count in merchant_counts.items():
        if count < 2:
            continue
        merchant_rows = [p for p in parsed if p.merchant.lower() == merchant]
        late_month_ratio = sum(1 for p in merchant_rows if _month_day(p.timestamp) >= 24) / len(merchant_rows)
        recurring = late_month_ratio >= 0.5
        if recurring:
            text = f"User frequently purchases from {merchant.title()} near end of month."
            writes.append(
                store.write(
                    {
                        "text": text,
                        "source": source,
                        "tags": ["finance", "recurring", "finance/recurring", merchant],
                        "confidence": 0.86,
                        "metadata": {
                            "merchant": merchant,
                            "count": len(merchant_rows),
                            "late_month_ratio": round(late_month_ratio, 3),
                        },
                    }
                )
            )

    return {"status": "ok", "writes": writes, "count": len(writes)}


def capture_flow_cron_setup(
    cron_expression: str,
    job_name: str,
    root: str = "memory",
    source: str = "clawflow/cron",
) -> dict[str, Any]:
    store = MemoryStore(root)
    text = f"Cron job '{job_name}' installed with schedule '{cron_expression}'."
    return store.write(
        {
            "text": text,
            "source": source,
            "tags": ["flow", "cron", "setup"],
            "confidence": 0.92,
            "metadata": {"job_name": job_name, "cron": cron_expression},
        }
    )


def capture_flow_job_failure(
    job_name: str,
    fail_reason: str,
    remind_in_seconds: int = 300,
    root: str = "memory",
) -> dict[str, Any]:
    store = MemoryStore(root)
    store.write(
        {
            "text": f"Job '{job_name}' failed: {fail_reason}",
            "source": "clawflow/failures",
            "tags": ["flow", "cron", "failure"],
            "confidence": 0.9,
            "metadata": {"job_name": job_name, "reason": fail_reason},
        }
    )
    engine = CommitmentEngine(root)
    return engine.create(
        text=f"Check failed job '{job_name}' and notify status update.",
        due_in_seconds=remind_in_seconds,
        metadata={"job_name": job_name, "kind": "flow_job_failure"},
    )


def capture_wizard_preference(
    mode: str,
    root: str = "memory",
    source: str = "clawwizard/preferences",
) -> dict[str, Any]:
    store = MemoryStore(root)
    normalized = mode.strip().lower()
    if normalized not in {"interactive", "cli"}:
        raise ValueError("mode must be 'interactive' or 'cli'")
    text = f"User prefers {normalized} wizard mode for setup workflows."
    return store.write(
        {
            "text": text,
            "source": source,
            "tags": ["wizard", "preference", normalized],
            "confidence": 0.93,
            "metadata": {"wizard_mode": normalized},
        }
    )
