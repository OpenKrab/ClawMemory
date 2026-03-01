from clawmemory.autocapture import CaptureConfig, extract_reusable_facts


def test_extract_reusable_facts() -> None:
    conversation = [
        {"role": "user", "content": "I prefer wizard setup and do not use raw CLI."},
        {"role": "assistant", "content": "Currently working on receipt parser optimization."},
        {"role": "user", "content": "ok"},
    ]

    facts = extract_reusable_facts(conversation, config=CaptureConfig(min_confidence=0.6))
    assert len(facts) >= 2
    assert any("preference" in fact["tags"] for fact in facts)
