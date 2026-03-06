from __future__ import annotations

import argparse
import json
from pathlib import Path

from .autocapture import CaptureConfig, extract_reusable_facts
from .tools import (
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
from .commitments import CommitmentEngine
from .tui_utils import (
    print_banner,
    print_section,
    print_key_value,
    print_success,
    print_info,
    COLORS
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="clawmemory")
    parser.add_argument("--root", default="memory", help="Memory root directory")

    sub = parser.add_subparsers(dest="command", required=True)

    write_cmd = sub.add_parser("write", help="Write one memory entry")
    write_cmd.add_argument("--payload", required=True, help="JSON payload")

    search_cmd = sub.add_parser("search", help="Search memories")
    search_cmd.add_argument("--query", required=True)
    search_cmd.add_argument("-k", type=int, default=5)

    get_cmd = sub.add_parser("get", help="Get memory by id")
    get_cmd.add_argument("--id", required=True)

    capture_cmd = sub.add_parser("autocapture", help="Extract reusable facts from conversation JSON")
    capture_cmd.add_argument("--conversation", required=True, help="Path to conversation JSON list")
    capture_cmd.add_argument("--min-confidence", type=float, default=0.7)
    capture_cmd.add_argument("--write", action="store_true", help="Write extracted memories")

    distill_cmd = sub.add_parser("distill", help="Build weekly curated/profile memory")
    distill_cmd.add_argument("--days", type=int, default=7)

    append_cmd = sub.add_parser("session-append", help="Append one turn into short-term session buffer")
    append_cmd.add_argument("--session-id", required=True)
    append_cmd.add_argument("--role", required=True, choices=["user", "assistant", "system"])
    append_cmd.add_argument("--content", required=True)
    append_cmd.add_argument("--auto-flush-max-turns", type=int, default=24)
    append_cmd.add_argument("--min-confidence", type=float, default=0.7)

    peek_cmd = sub.add_parser("session-peek", help="Peek session buffer")
    peek_cmd.add_argument("--session-id", required=True)
    peek_cmd.add_argument("--limit", type=int, default=None)

    flush_cmd = sub.add_parser("session-flush", help="Flush session buffer into long-term memory")
    flush_cmd.add_argument("--session-id", required=True)
    flush_cmd.add_argument("--min-confidence", type=float, default=0.7)
    flush_cmd.add_argument("--keep-buffer", action="store_true")

    reminder_set_cmd = sub.add_parser("reminder-set", help="Create reminder/commitment")
    reminder_set_cmd.add_argument("--text", required=True)
    reminder_set_cmd.add_argument("--in-seconds", type=int, default=None)
    reminder_set_cmd.add_argument("--due-at", default=None, help="ISO timestamp (UTC preferred)")
    reminder_set_cmd.add_argument("--session-id", default=None)

    reminder_list_cmd = sub.add_parser("reminder-list", help="List reminders")
    reminder_list_cmd.add_argument("--status", default=None)
    reminder_list_cmd.add_argument("--limit", type=int, default=200)

    reminder_done_cmd = sub.add_parser("reminder-complete", help="Complete reminder")
    reminder_done_cmd.add_argument("--id", required=True)
    reminder_done_cmd.add_argument("--note", default=None)

    reminder_snooze_cmd = sub.add_parser("reminder-snooze", help="Snooze reminder by seconds")
    reminder_snooze_cmd.add_argument("--id", required=True)
    reminder_snooze_cmd.add_argument("--seconds", type=int, required=True)

    reminder_poll_cmd = sub.add_parser("reminder-poll", help="Poll due reminders and mark overdue")
    reminder_poll_cmd.add_argument("--limit", type=int, default=50)

    reminder_watch_cmd = sub.add_parser("reminder-watch", help="Run event-loop reminder watcher")
    reminder_watch_cmd.add_argument("--interval", type=float, default=1.0)
    reminder_watch_cmd.add_argument("--max-sleep", type=float, default=30.0)

    sub.add_parser("stats", help="Show memory statistics (TUI style)")

    args = parser.parse_args()
    root = Path(args.root)

    if args.command == "write":
        payload = json.loads(args.payload)
        print(json.dumps(memory_write(payload=payload, root=root), indent=2))
        return

    if args.command == "search":
        print(json.dumps(memory_search(query=args.query, k=args.k, root=root), indent=2))
        return

    if args.command == "get":
        print(json.dumps(memory_get(memory_id=args.id, root=root), indent=2))
        return

    if args.command == "autocapture":
        turns = json.loads(Path(args.conversation).read_text(encoding="utf-8"))
        extracted = extract_reusable_facts(
            conversation=turns,
            config=CaptureConfig(min_confidence=args.min_confidence),
        )
        result = {"extracted": extracted, "count": len(extracted)}
        if args.write:
            writes = [memory_write(payload=item, root=root) for item in extracted]
            result["writes"] = writes
        print(json.dumps(result, indent=2))
        return

    if args.command == "distill":
        print(json.dumps(memory_distill(root=root, days=args.days), indent=2))
        return

    if args.command == "session-append":
        print(
            json.dumps(
                memory_session_append(
                    session_id=args.session_id,
                    role=args.role,
                    content=args.content,
                    root=root,
                    auto_flush_max_turns=args.auto_flush_max_turns,
                    min_confidence=args.min_confidence,
                ),
                indent=2,
            )
        )
        return

    if args.command == "session-peek":
        print(json.dumps(memory_session_peek(session_id=args.session_id, root=root, limit=args.limit), indent=2))
        return

    if args.command == "session-flush":
        print(
            json.dumps(
                memory_session_flush(
                    session_id=args.session_id,
                    root=root,
                    min_confidence=args.min_confidence,
                    keep_buffer=args.keep_buffer,
                ),
                indent=2,
            )
        )
        return

    if args.command == "reminder-set":
        print(
            json.dumps(
                reminder_set(
                    text=args.text,
                    due_in_seconds=args.in_seconds,
                    due_at=args.due_at,
                    session_id=args.session_id,
                    root=root,
                ),
                indent=2,
            )
        )
        return

    if args.command == "reminder-list":
        print(
            json.dumps(
                reminder_status(root=root, status=args.status, limit=args.limit),
                indent=2,
            )
        )
        return

    if args.command == "reminder-complete":
        print(json.dumps(reminder_complete(reminder_id=args.id, root=root, note=args.note), indent=2))
        return

    if args.command == "reminder-snooze":
        print(json.dumps(reminder_snooze(reminder_id=args.id, seconds=args.seconds, root=root), indent=2))
        return

    if args.command == "reminder-poll":
        print(json.dumps(reminder_poll(root=root, limit=args.limit), indent=2))
        return

    if args.command == "reminder-watch":
        engine = CommitmentEngine(root)
        engine.watch(interval_seconds=args.interval, max_sleep_seconds=args.max_sleep)
        return

    if args.command == "stats":
        from .store import MemoryStore
        from .commitments import CommitmentEngine

        store = MemoryStore(root)
        commitments = CommitmentEngine(root)

        total = store.count()
        health = commitments.health()

        print_banner()
        print_section("General Statistics")
        print_key_value("Total Memories", str(total))
        print_key_value("Root Directory", str(root))

        print_section("Commitment Health")
        print_key_value("Pending", str(health["counts"]["pending"]))
        print_key_value("Overdue", str(health["counts"]["overdue"]))
        print_key_value("Completed", str(health["counts"]["completed"]))
        print_key_value("Due Soon (5m)", str(health["due_soon_5m"]))

        print_section("System Status")
        print_success("Database integration: OK")
        print_info(f"Last update: {health['now']}")
        return


if __name__ == "__main__":
    main()
