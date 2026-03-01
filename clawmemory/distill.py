from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .store import MemoryStore


def _to_utc(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _unique_texts(entries: list[dict[str, Any]], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for entry in entries:
        text = " ".join(str(entry.get("text", "")).split())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
        if len(items) >= limit:
            break
    return items


def weekly_distill(root: str | Path = "memory", days: int = 7) -> dict[str, object]:
    store = MemoryStore(root)
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=days)

    entries = store.all_entries()
    recent = [e for e in entries if _to_utc(e["timestamp"]) >= threshold]

    top_tags = Counter(tag for e in recent for tag in e.get("tags", []))
    highlights = sorted(recent, key=lambda item: item.get("confidence", 0), reverse=True)[:10]

    preference_entries = sorted(
        [e for e in entries if "preference" in e.get("tags", [])],
        key=lambda item: item.get("confidence", 0),
        reverse=True,
    )
    constraint_entries = sorted(
        [e for e in entries if "constraint" in e.get("tags", [])],
        key=lambda item: item.get("confidence", 0),
        reverse=True,
    )
    ongoing_entries = sorted(
        [e for e in entries if "ongoing_task" in e.get("tags", [])],
        key=lambda item: item.get("confidence", 0),
        reverse=True,
    )

    preferences = _unique_texts(preference_entries, limit=10)
    constraints = _unique_texts(constraint_entries, limit=10)
    ongoing = _unique_texts(ongoing_entries, limit=10)

    curated = store.curated_path
    curated_lines = [
        "# ClawMemory Curated",
        "",
        f"## Weekly Distill ({now.date().isoformat()})",
        "",
        f"- Entries considered: {len(recent)}",
        f"- Top tags: {', '.join(f'{k}({v})' for k, v in top_tags.most_common(5)) or 'n/a'}",
        "",
        "### Highlights",
    ]
    for item in highlights:
        curated_lines.append(f"- [{item['id']}] ({item['source']}) {item['text'][:160]}")
    curated.write_text("\n".join(curated_lines) + "\n", encoding="utf-8")

    profile = store.profile_path
    profile_lines = [
        "# Profile",
        "",
        f"## Distilled At\n- {now.isoformat(timespec='seconds')}",
        "",
        "## Preferences",
    ]
    if preferences:
        profile_lines.extend([f"- {item}" for item in preferences])
    else:
        profile_lines.append("- n/a")

    profile_lines.append("")
    profile_lines.append("## Constraints")
    if constraints:
        profile_lines.extend([f"- {item}" for item in constraints])
    else:
        profile_lines.append("- n/a")

    profile_lines.append("")
    profile_lines.append("## Ongoing Tasks")
    if ongoing:
        profile_lines.extend([f"- {item}" for item in ongoing])
    else:
        profile_lines.append("- n/a")

    profile.write_text("\n".join(profile_lines) + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "curated_path": str(curated),
        "profile_path": str(profile),
        "entries_considered": len(recent),
        "top_tags": dict(top_tags.most_common(5)),
        "profile_counts": {
            "preferences": len(preferences),
            "constraints": len(constraints),
            "ongoing_tasks": len(ongoing),
        },
    }
