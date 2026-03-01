from __future__ import annotations

from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from .store import MemoryStore


def precision_at_k(
    root: str | Path,
    queries: list[dict[str, Any]],
    k: int = 5,
) -> float:
    store = MemoryStore(root)
    values: list[float] = []
    for q in queries:
        expected = set(q.get("expected_ids", []))
        if not expected:
            continue
        results = store.search(q["query"], k=k)["results"]
        got = {item["id"] for item in results}
        values.append(len(got & expected) / min(k, len(expected)))
    return mean(values) if values else 0.0


def latency_ms(root: str | Path, sample_queries: list[str], k: int = 5) -> float:
    store = MemoryStore(root)
    values: list[float] = []
    for query in sample_queries:
        started = perf_counter()
        store.search(query=query, k=k)
        values.append((perf_counter() - started) * 1000)
    return round(mean(values), 2) if values else 0.0


def duplicate_rate(write_results: list[dict[str, Any]]) -> float:
    if not write_results:
        return 0.0
    dups = sum(1 for item in write_results if item.get("status") == "deduplicated")
    return round(dups / len(write_results), 4)


def memory_growth_rate(root: str | Path, previous_count: int, current_count: int) -> float:
    _ = MemoryStore(root)
    if previous_count <= 0:
        return 1.0 if current_count > 0 else 0.0
    return round((current_count - previous_count) / previous_count, 4)
