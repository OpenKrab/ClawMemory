from pathlib import Path

from clawmemory.tools import (
    memory_distill,
    memory_search,
    memory_session_append,
    memory_session_flush,
    memory_session_peek,
    memory_write,
)


def test_search_includes_snippet_and_prompt_context(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    memory_write(
        {
            "text": "User prefers interactive wizard setup and avoids raw CLI commands for cron jobs.",
            "source": "clawwizard/session",
            "tags": ["preference"],
            "confidence": 0.95,
        },
        root=root,
    )

    result = memory_search("wizard cron", k=3, root=root)
    assert len(result["results"]) == 1
    top = result["results"][0]
    assert "snippet" in top
    assert "wizard" in top["snippet"].lower()
    assert "prompt_context" in result
    assert "<relevant-memories>" in result["prompt_context"]


def test_session_buffer_append_peek_flush(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    session_id = "s1"

    out1 = memory_session_append(
        session_id=session_id,
        role="user",
        content="I prefer wizard setup and do not use raw CLI.",
        root=root,
        auto_flush_max_turns=10,
        min_confidence=0.6,
    )
    assert out1["status"] == "buffered"

    out2 = memory_session_append(
        session_id=session_id,
        role="assistant",
        content="Currently working on receipt categorization constraints.",
        root=root,
        auto_flush_max_turns=10,
        min_confidence=0.6,
    )
    assert out2["turns_in_buffer"] == 2

    peek = memory_session_peek(session_id=session_id, root=root)
    assert peek["count"] == 2

    flushed = memory_session_flush(session_id=session_id, root=root, min_confidence=0.6)
    assert flushed["status"] == "flushed"
    assert flushed["extracted_count"] >= 1


def test_distill_updates_profile(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    memory_write(
        {
            "text": "I prefer wizard setup for daily automation.",
            "source": "clawflow/session",
            "tags": ["preference"],
            "confidence": 0.9,
        },
        root=root,
    )
    memory_write(
        {
            "text": "Do not run heavy jobs during office hours.",
            "source": "clawflow/session",
            "tags": ["constraint"],
            "confidence": 0.86,
        },
        root=root,
    )

    out = memory_distill(root=root, days=7)
    assert out["status"] == "ok"

    profile = Path(out["profile_path"]).read_text(encoding="utf-8")
    assert "## Preferences" in profile
    assert "## Constraints" in profile
