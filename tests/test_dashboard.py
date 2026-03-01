from pathlib import Path

from clawmemory.dashboard import build_dashboard_snapshot
from clawmemory.tools import memory_write


def test_build_dashboard_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    memory_write(
        {
            "text": "User prefers wizard-based setup for flow management.",
            "source": "clawflow/session",
            "tags": ["preference", "flow"],
            "confidence": 0.92,
        },
        root=root,
    )
    memory_write(
        {
            "text": "Do not execute heavy cron between 09:00-18:00.",
            "source": "clawwizard/session",
            "tags": ["constraint", "cron"],
            "confidence": 0.84,
        },
        root=root,
    )

    snap = build_dashboard_snapshot(root=root, limit=50)
    assert snap["stats"]["total_memories"] == 2
    assert snap["stats"]["distinct_sources"] == 2
    assert len(snap["timeline"]) == 2
    assert any(tag == "preference" for tag, _ in snap["top_tags"])
