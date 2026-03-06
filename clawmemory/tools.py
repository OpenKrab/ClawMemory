from __future__ import annotations

from pathlib import Path
from typing import Any

from .commitments import CommitmentEngine
from .distill import weekly_distill
from .integrations import (
    capture_flow_cron_setup,
    capture_flow_job_failure,
    capture_receipt_patterns,
    capture_wizard_preference,
    capture_graph_entities,
)
from .session_buffer import SessionBuffer
from .store import MemoryStore


def memory_write(payload: dict[str, Any], root: str | Path = "memory") -> dict[str, Any]:
    store = MemoryStore(root)
    return store.write(payload)


def memory_search(
    query: str,
    k: int = 5,
    root: str | Path = "memory",
    include_prompt_context: bool = True,
) -> dict[str, Any]:
    store = MemoryStore(root)
    return store.search(query=query, k=k, include_prompt_context=include_prompt_context)


def memory_get(memory_id: str, root: str | Path = "memory") -> dict[str, Any] | None:
    store = MemoryStore(root)
    return store.get(memory_id)


def memory_session_append(
    session_id: str,
    role: str,
    content: str,
    root: str | Path = "memory",
    auto_flush_max_turns: int = 24,
    min_confidence: float = 0.7,
) -> dict[str, Any]:
    buffer = SessionBuffer(root)
    return buffer.append_turn(
        session_id=session_id,
        role=role,
        content=content,
        auto_flush_max_turns=auto_flush_max_turns,
        min_confidence=min_confidence,
    )


def memory_session_peek(
    session_id: str,
    root: str | Path = "memory",
    limit: int | None = None,
) -> dict[str, Any]:
    buffer = SessionBuffer(root)
    turns = buffer.read_turns(session_id=session_id, limit=limit)
    return {
        "status": "ok",
        "session_id": session_id,
        "count": len(turns),
        "turns": turns,
    }


def memory_session_flush(
    session_id: str,
    root: str | Path = "memory",
    min_confidence: float = 0.7,
    keep_buffer: bool = False,
) -> dict[str, Any]:
    buffer = SessionBuffer(root)
    return buffer.flush_session(
        session_id=session_id,
        min_confidence=min_confidence,
        keep_buffer=keep_buffer,
    )


def memory_distill(root: str | Path = "memory", days: int = 7) -> dict[str, object]:
    return weekly_distill(root=root, days=days)


def reminder_set(
    text: str,
    root: str | Path = "memory",
    due_in_seconds: int | None = None,
    due_at: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    engine = CommitmentEngine(root)
    return engine.create(
        text=text,
        due_in_seconds=due_in_seconds,
        due_at=due_at,
        session_id=session_id,
        metadata=metadata,
    )


def reminder_status(
    root: str | Path = "memory",
    status: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    engine = CommitmentEngine(root)
    return {
        "status": "ok",
        "items": engine.list(status=status, limit=limit),
        "health": engine.health(),
    }


def reminder_complete(
    reminder_id: str,
    root: str | Path = "memory",
    note: str | None = None,
) -> dict[str, Any]:
    engine = CommitmentEngine(root)
    row = engine.complete(reminder_id, note=note)
    if row is None:
        return {"status": "not_found", "id": reminder_id}
    return {"status": "ok", "item": row}


def reminder_snooze(
    reminder_id: str,
    seconds: int,
    root: str | Path = "memory",
) -> dict[str, Any]:
    engine = CommitmentEngine(root)
    row = engine.snooze(reminder_id, seconds=seconds)
    if row is None:
        return {"status": "not_found", "id": reminder_id}
    return {"status": "ok", "item": row}


def reminder_poll(root: str | Path = "memory", limit: int = 50) -> dict[str, Any]:
    engine = CommitmentEngine(root)
    return engine.poll_due(limit=limit)


def integration_capture_receipts(
    events: list[dict[str, Any]],
    root: str | Path = "memory",
) -> dict[str, Any]:
    return capture_receipt_patterns(events=events, root=str(root))


def integration_flow_cron_setup(
    cron_expression: str,
    job_name: str,
    root: str | Path = "memory",
) -> dict[str, Any]:
    return capture_flow_cron_setup(cron_expression=cron_expression, job_name=job_name, root=str(root))


def integration_flow_job_failure(
    job_name: str,
    fail_reason: str,
    remind_in_seconds: int = 300,
    root: str | Path = "memory",
) -> dict[str, Any]:
    return capture_flow_job_failure(
        job_name=job_name,
        fail_reason=fail_reason,
        remind_in_seconds=remind_in_seconds,
        root=str(root),
    )


def integration_wizard_preference(
    mode: str,
    root: str | Path = "memory",
) -> dict[str, Any]:
    return capture_wizard_preference(mode=mode, root=str(root))


def integration_graph_sync(
    entities: dict[str, list[dict[str, Any]]],
    root: str | Path = "memory",
) -> dict[str, Any]:
    return capture_graph_entities(entities=entities, root=str(root))
