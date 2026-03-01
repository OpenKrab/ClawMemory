from pathlib import Path

from clawmemory.openclaw_bridge import main


def test_bridge_roundtrip(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "memory"

    monkeypatch.setattr("sys.argv", ["bridge", "write", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{"text":"remember this","source":"test"}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "stored" in out

    monkeypatch.setattr("sys.argv", ["bridge", "search", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{"query":"remember","k":3}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "results" in out


def test_bridge_session_and_distill(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "memory"

    monkeypatch.setattr("sys.argv", ["bridge", "session_append", "--root", str(root)])
    monkeypatch.setattr(
        "sys.stdin.read",
        lambda: '{"session_id":"s1","role":"user","content":"I prefer wizard setup"}',
    )
    assert main() == 0
    out = capsys.readouterr().out
    assert "buffered" in out

    monkeypatch.setattr("sys.argv", ["bridge", "session_flush", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{"session_id":"s1","min_confidence":0.6}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "flushed" in out

    monkeypatch.setattr("sys.argv", ["bridge", "distill", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{"days":7}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "profile_path" in out


def test_bridge_reminders(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "memory"

    monkeypatch.setattr("sys.argv", ["bridge", "reminder_set", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{"text":"ping in 5m","due_in_seconds":300}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "pending" in out

    monkeypatch.setattr("sys.argv", ["bridge", "reminder_status", "--root", str(root)])
    monkeypatch.setattr("sys.stdin.read", lambda: '{}')
    assert main() == 0
    out = capsys.readouterr().out
    assert "items" in out
