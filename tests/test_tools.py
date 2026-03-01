from pathlib import Path

from clawmemory.distill import weekly_distill
from clawmemory.tools import memory_get, memory_search, memory_write


def test_memory_write_search_get(tmp_path: Path) -> None:
    root = tmp_path / "memory"

    first = memory_write(
        {
            "text": "User prefers interactive wizard over CLI for cron setup.",
            "source": "clawwizard/session",
            "tags": ["preference", "wizard"],
            "confidence": 0.91,
        },
        root=root,
    )
    assert first["status"] == "stored"

    duplicate = memory_write(
        {
            "text": "User prefers interactive wizard over CLI for cron setup.",
            "source": "clawwizard/session",
            "tags": ["preference", "wizard"],
            "confidence": 0.91,
        },
        root=root,
    )
    assert duplicate["status"] == "deduplicated"

    search = memory_search("interactive wizard cron", k=3, root=root)
    assert len(search["results"]) == 1
    assert search["results"][0]["id"] == first["id"]

    got = memory_get(first["id"], root=root)
    assert got is not None
    assert got["provenance"]["event_path"].endswith(f"{first['id']}.md")


def test_weekly_distill(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    memory_write(
        {
            "text": "Current task is building receipt anomaly checks every Friday.",
            "source": "clawreceipt/agent",
            "tags": ["ongoing_task", "receipt"],
            "confidence": 0.85,
        },
        root=root,
    )

    out = weekly_distill(root=root, days=7)
    assert out["status"] == "ok"
    assert Path(out["curated_path"]).exists()
    assert Path(out["profile_path"]).exists()
