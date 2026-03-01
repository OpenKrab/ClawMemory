from pathlib import Path

from clawmemory.tools import (
    integration_capture_receipts,
    integration_flow_cron_setup,
    integration_flow_job_failure,
    integration_wizard_preference,
    reminder_status,
)


def test_capture_receipt_patterns(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    out = integration_capture_receipts(
        events=[
            {"merchant": "Shopee", "amount": 500.0, "timestamp": "2026-01-25T10:00:00+00:00"},
            {"merchant": "Shopee", "amount": 700.0, "timestamp": "2026-02-26T10:00:00+00:00"},
            {"merchant": "Lazada", "amount": 100.0, "timestamp": "2026-02-03T10:00:00+00:00"},
        ],
        root=root,
    )
    assert out["status"] == "ok"
    assert out["count"] >= 1


def test_capture_flow_and_wizard(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    cron = integration_flow_cron_setup("0 9 * * *", "daily-report", root=root)
    assert cron["status"] in {"stored", "deduplicated"}

    failed = integration_flow_job_failure("daily-report", "timeout", remind_in_seconds=60, root=root)
    assert "id" in failed

    pref = integration_wizard_preference("interactive", root=root)
    assert pref["status"] in {"stored", "deduplicated"}

    reminders = reminder_status(root=root)
    assert reminders["health"]["counts"]["pending"] >= 1
