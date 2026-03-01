from pathlib import Path

from clawmemory.tools import (
    reminder_complete,
    reminder_poll,
    reminder_set,
    reminder_snooze,
    reminder_status,
)


def test_reminder_lifecycle(tmp_path: Path) -> None:
    root = tmp_path / "memory"

    created = reminder_set(text="send follow-up in 1s", due_in_seconds=1, root=root)
    rid = created["id"]
    assert created["status"] == "pending"

    listed = reminder_status(root=root)
    assert listed["status"] == "ok"
    assert any(item["id"] == rid for item in listed["items"])

    snoozed = reminder_snooze(reminder_id=rid, seconds=120, root=root)
    assert snoozed["status"] == "ok"
    assert snoozed["item"]["status"] == "pending"

    polled = reminder_poll(root=root, limit=10)
    assert polled["status"] == "ok"

    done = reminder_complete(reminder_id=rid, root=root, note="done")
    assert done["status"] == "ok"
    assert done["item"]["status"] == "completed"
