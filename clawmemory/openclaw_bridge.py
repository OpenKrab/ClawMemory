from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .tools import (
    integration_capture_receipts,
    integration_flow_cron_setup,
    integration_flow_job_failure,
    integration_wizard_preference,
    memory_distill,
    memory_get,
    memory_search,
    memory_session_append,
    memory_session_flush,
    memory_session_peek,
    memory_write,
    reminder_complete,
    reminder_poll,
    reminder_set,
    reminder_snooze,
    reminder_status,
)


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(prog="clawmemory.openclaw_bridge")
    parser.add_argument(
        "command",
        choices=[
            "write",
            "search",
            "get",
            "session_append",
            "session_peek",
            "session_flush",
            "distill",
            "reminder_set",
            "reminder_status",
            "reminder_complete",
            "reminder_snooze",
            "reminder_poll",
            "integration_capture_receipts",
            "integration_flow_cron_setup",
            "integration_flow_job_failure",
            "integration_wizard_preference",
        ],
    )
    parser.add_argument("--root", default="memory")
    args = parser.parse_args()

    root = Path(args.root)
    payload = _read_stdin_json()

    if args.command == "write":
        result = memory_write(payload=payload, root=root)
        print(json.dumps(result))
        return 0

    if args.command == "search":
        query = str(payload.get("query", "")).strip()
        k = int(payload.get("k", 5) or 5)
        result = memory_search(query=query, k=max(1, k), root=root)
        print(json.dumps(result))
        return 0

    if args.command == "get":
        memory_id = str(payload.get("id", "")).strip()
        result = memory_get(memory_id=memory_id, root=root)
        if result is None:
            print(json.dumps({"not_found": True, "id": memory_id}))
            return 0
        print(json.dumps(result))
        return 0

    if args.command == "session_append":
        result = memory_session_append(
            session_id=str(payload.get("session_id", "")).strip(),
            role=str(payload.get("role", "user")).strip() or "user",
            content=str(payload.get("content", "")).strip(),
            root=root,
            auto_flush_max_turns=int(payload.get("auto_flush_max_turns", 24) or 24),
            min_confidence=float(payload.get("min_confidence", 0.7) or 0.7),
        )
        print(json.dumps(result))
        return 0

    if args.command == "session_peek":
        limit_raw = payload.get("limit", None)
        limit = int(limit_raw) if isinstance(limit_raw, int) else None
        result = memory_session_peek(
            session_id=str(payload.get("session_id", "")).strip(),
            root=root,
            limit=limit,
        )
        print(json.dumps(result))
        return 0

    if args.command == "session_flush":
        result = memory_session_flush(
            session_id=str(payload.get("session_id", "")).strip(),
            root=root,
            min_confidence=float(payload.get("min_confidence", 0.7) or 0.7),
            keep_buffer=bool(payload.get("keep_buffer", False)),
        )
        print(json.dumps(result))
        return 0

    if args.command == "reminder_set":
        result = reminder_set(
            text=str(payload.get("text", "")).strip(),
            due_in_seconds=int(payload.get("due_in_seconds", 300) or 300),
            due_at=str(payload.get("due_at", "")).strip() or None,
            session_id=str(payload.get("session_id", "")).strip() or None,
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
            root=root,
        )
        print(json.dumps(result))
        return 0

    if args.command == "reminder_status":
        result = reminder_status(
            root=root,
            status=str(payload.get("status", "")).strip() or None,
            limit=int(payload.get("limit", 200) or 200),
        )
        print(json.dumps(result))
        return 0

    if args.command == "reminder_complete":
        result = reminder_complete(
            reminder_id=str(payload.get("id", "")).strip(),
            note=str(payload.get("note", "")).strip() or None,
            root=root,
        )
        print(json.dumps(result))
        return 0

    if args.command == "reminder_snooze":
        result = reminder_snooze(
            reminder_id=str(payload.get("id", "")).strip(),
            seconds=int(payload.get("seconds", 60) or 60),
            root=root,
        )
        print(json.dumps(result))
        return 0

    if args.command == "reminder_poll":
        result = reminder_poll(root=root, limit=int(payload.get("limit", 50) or 50))
        print(json.dumps(result))
        return 0

    if args.command == "integration_capture_receipts":
        events = payload.get("events", [])
        if not isinstance(events, list):
            events = []
        result = integration_capture_receipts(events=events, root=root)
        print(json.dumps(result))
        return 0

    if args.command == "integration_flow_cron_setup":
        result = integration_flow_cron_setup(
            cron_expression=str(payload.get("cron_expression", "")).strip(),
            job_name=str(payload.get("job_name", "")).strip(),
            root=root,
        )
        print(json.dumps(result))
        return 0

    if args.command == "integration_flow_job_failure":
        result = integration_flow_job_failure(
            job_name=str(payload.get("job_name", "")).strip(),
            fail_reason=str(payload.get("fail_reason", "")).strip(),
            remind_in_seconds=int(payload.get("remind_in_seconds", 300) or 300),
            root=root,
        )
        print(json.dumps(result))
        return 0

    if args.command == "integration_wizard_preference":
        result = integration_wizard_preference(
            mode=str(payload.get("mode", "")).strip(),
            root=root,
        )
        print(json.dumps(result))
        return 0

    result = memory_distill(root=root, days=int(payload.get("days", 7) or 7))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
