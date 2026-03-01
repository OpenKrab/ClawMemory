from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .commitments import CommitmentEngine
from .tools import memory_distill, memory_get, memory_search, reminder_complete, reminder_poll, reminder_status
from .store import MemoryStore


def _to_utc(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_dashboard_snapshot(root: str | Path, limit: int = 200) -> dict[str, Any]:
    store = MemoryStore(root)
    reminders = CommitmentEngine(root)
    entries = store.all_entries()
    entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)

    now = datetime.now(timezone.utc)
    recent_threshold = now - timedelta(days=7)
    recent_7d = [e for e in entries if _to_utc(str(e.get("timestamp", now.isoformat()))) >= recent_threshold]

    top_tags = Counter(tag for e in entries for tag in e.get("tags", []))
    top_sources = Counter(str(e.get("source", "")) for e in entries if e.get("source"))

    confidences = [float(e.get("confidence", 0)) for e in entries]
    avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    sessions_dir = Path(root) / "sessions"
    session_files = sorted(sessions_dir.glob("*.jsonl")) if sessions_dir.exists() else []
    reminder_health = reminders.health()

    return {
        "stats": {
            "total_memories": len(entries),
            "recent_7d": len(recent_7d),
            "avg_confidence": avg_confidence,
            "distinct_sources": len(top_sources),
            "session_buffers": len(session_files),
            "reminders_pending": reminder_health["counts"]["pending"],
            "reminders_overdue": reminder_health["counts"]["overdue"],
        },
        "reminders": reminder_health,
        "top_tags": top_tags.most_common(12),
        "top_sources": top_sources.most_common(12),
        "timeline": entries[:limit],
    }


def _list_sessions(root: str | Path) -> list[dict[str, Any]]:
    sessions_dir = Path(root) / "sessions"
    if not sessions_dir.exists():
        return []

    out: list[dict[str, Any]] = []
    for file in sorted(sessions_dir.glob("*.jsonl"), reverse=True):
        try:
            lines = [ln for ln in file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError:
            lines = []
        out.append(
            {
                "session_id": file.stem,
                "path": str(file),
                "turns": len(lines),
                "size_bytes": file.stat().st_size if file.exists() else 0,
            }
        )
    return out


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>ClawMemory Dashboard</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap\" rel=\"stylesheet\">
  <style>
    :root {
      --bg-0: #f0f4ff;
      --bg-1: #d9e7ff;
      --ink: #0f172a;
      --muted: #42526b;
      --card: #ffffffd9;
      --line: #b9cae5;
      --accent: #0ea5a4;
      --accent-2: #f97316;
      --good: #16a34a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Space Grotesk", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 15% 10%, #c8d8ff 0, transparent 35%),
        radial-gradient(circle at 80% 0%, #b8f0ec 0, transparent 30%),
        linear-gradient(120deg, var(--bg-0), var(--bg-1));
      min-height: 100vh;
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .title {
      display: flex; justify-content: space-between; align-items: end; gap: 12px;
      margin-bottom: 14px;
    }
    h1 { margin: 0; font-size: clamp(28px, 6vw, 46px); line-height: 1; }
    .sub { color: var(--muted); font-size: 14px; }
    .mono { font-family: "IBM Plex Mono", monospace; font-size: 12px; }
    .grid { display: grid; gap: 14px; }
    .stats { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-bottom: 14px; }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      box-shadow: 0 8px 30px #08306b14;
      backdrop-filter: blur(5px);
    }
    .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .v { font-size: 28px; font-weight: 700; margin-top: 5px; }
    .layout { grid-template-columns: 1.2fr .8fr; }
    .panel-title { font-size: 17px; margin: 0 0 10px; }
    .toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
    input, button {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 11px;
      font: inherit;
    }
    input { flex: 1; background: #fff; }
    button {
      background: linear-gradient(160deg, var(--accent), #0284c7);
      color: #fff; border: 0; cursor: pointer; font-weight: 600;
      transition: transform .12s ease;
    }
    button:hover { transform: translateY(-1px); }
    button.alt { background: linear-gradient(160deg, var(--accent-2), #fb7185); }
    .list { display: grid; gap: 8px; max-height: 430px; overflow: auto; padding-right: 3px; }
    .item {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      background: #fff;
      animation: fadeIn .2s ease both;
    }
    .item-head { display: flex; justify-content: space-between; gap: 10px; }
    .item-src { font-weight: 700; font-size: 13px; }
    .item-time { color: var(--muted); font-size: 11px; }
    .item-body { margin-top: 6px; color: #1e293b; font-size: 13px; line-height: 1.4; }
    .tags { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 6px; }
    .tag {
      border: 1px solid #c5d6f1;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      background: #eef5ff;
    }
    .pill { padding: 3px 8px; border-radius: 999px; font-size: 11px; border: 1px solid #b9eec8; color: var(--good); }
    .side { display: grid; gap: 14px; }
    ul { margin: 0; padding-left: 18px; }
    li { margin: 6px 0; }
    .empty { color: var(--muted); font-size: 13px; }
    @keyframes fadeIn { from {opacity:0; transform: translateY(3px);} to {opacity:1; transform:none;} }
    @media (max-width: 940px) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"title\">
      <div>
        <h1>ClawMemory UI</h1>
        <div class=\"sub\">Timeline, recall, health, and sessions in one local dashboard.</div>
      </div>
      <div class=\"mono\" id=\"stamp\">loading...</div>
    </div>

    <div class=\"grid stats\" id=\"stats\"></div>

    <div class=\"grid layout\">
      <section class=\"card\">
        <h2 class=\"panel-title\">Memory Search</h2>
        <div class=\"toolbar\">
          <input id=\"q\" placeholder=\"Search memories... e.g. wizard cron preference\" />
          <button id=\"searchBtn\">Search</button>
          <button class=\"alt\" id=\"distillBtn\">Distill</button>
        </div>
        <div class=\"list\" id=\"results\"></div>
      </section>

      <aside class=\"side\">
        <section class=\"card\">
          <h2 class=\"panel-title\">Top Sources</h2>
          <ul id=\"sources\"></ul>
        </section>
        <section class=\"card\">
          <h2 class=\"panel-title\">Top Tags</h2>
          <ul id=\"tags\"></ul>
        </section>
        <section class=\"card\">
          <h2 class=\"panel-title\">Session Buffers</h2>
          <div class=\"list\" id=\"sessions\"></div>
        </section>
        <section class=\"card\">
          <h2 class=\"panel-title\">Commitments</h2>
          <div class=\"toolbar\">
            <button id=\"pollDueBtn\">Poll Due</button>
          </div>
          <div class=\"list\" id=\"commitments\"></div>
        </section>
      </aside>
    </div>
  </div>

<script>
const $ = (id) => document.getElementById(id);

function fmtTime(ts) {
  const d = new Date(ts);
  return isNaN(d) ? ts : d.toLocaleString();
}

function statCard(label, value) {
  return `<div class=\"card\"><div class=\"k\">${label}</div><div class=\"v\">${value}</div></div>`;
}

function memoryCard(item) {
  const tags = (item.tags || []).map((t) => `<span class=\"tag\">${t}</span>`).join(\"\");
  const score = item.scores && item.scores.hybrid !== undefined
    ? `<span class=\"pill\">score ${item.scores.hybrid}</span>`
    : \"\";
  return `
    <article class=\"item\">
      <div class=\"item-head\">
        <div class=\"item-src\">${item.source || \"unknown\"}</div>
        <div class=\"item-time\">${fmtTime(item.timestamp || \"\")}</div>
      </div>
      <div class=\"item-body\">${item.snippet || item.text || \"\"}</div>
      <div class=\"tags\">${tags}${score}</div>
    </article>
  `;
}

async function getJson(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function refreshSnapshot() {
  const snap = await getJson('/api/snapshot?limit=200');
  const s = snap.stats || {};
  $('stats').innerHTML = [
    statCard('Total Memories', s.total_memories ?? 0),
    statCard('Recent 7d', s.recent_7d ?? 0),
    statCard('Avg Confidence', s.avg_confidence ?? 0),
    statCard('Sources', s.distinct_sources ?? 0),
    statCard('Session Buffers', s.session_buffers ?? 0),
    statCard('Reminder Pending', s.reminders_pending ?? 0),
    statCard('Reminder Overdue', s.reminders_overdue ?? 0),
  ].join('');

  const timeline = snap.timeline || [];
  $('results').innerHTML = timeline.length ? timeline.map(memoryCard).join('') : '<div class=\"empty\">No memories yet</div>';

  const src = snap.top_sources || [];
  $('sources').innerHTML = src.length ? src.map(([k,v]) => `<li><code>${k}</code> (${v})</li>`).join('') : '<li class=\"empty\">n/a</li>';

  const tags = snap.top_tags || [];
  $('tags').innerHTML = tags.length ? tags.map(([k,v]) => `<li><code>${k}</code> (${v})</li>`).join('') : '<li class=\"empty\">n/a</li>';

  const sessions = await getJson('/api/sessions');
  $('sessions').innerHTML = (sessions.sessions || []).length
    ? sessions.sessions.map((s) => `<article class=\"item\"><div class=\"item-head\"><div class=\"item-src\">${s.session_id}</div><div class=\"item-time\">${s.turns} turn(s)</div></div><div class=\"item-body mono\">${s.path}</div></article>`).join('')
    : '<div class=\"empty\">No session buffers</div>';

  const reminders = await getJson('/api/commitments?status=');
  const items = reminders.items || [];
  $('commitments').innerHTML = items.length
    ? items.map((r) => `<article class=\"item\"><div class=\"item-head\"><div class=\"item-src\">${r.status}</div><div class=\"item-time\">due ${fmtTime(r.due_at || '')}</div></div><div class=\"item-body\">${r.text || ''}</div><div class=\"tags\"><span class=\"tag mono\">${r.id}</span></div></article>`).join('')
    : '<div class=\"empty\">No reminders</div>';

  $('stamp').textContent = `updated ${new Date().toLocaleTimeString()}`;
}

async function searchNow() {
  const q = $('q').value.trim();
  if (!q) {
    refreshSnapshot();
    return;
  }
  const data = await getJson(`/api/search?q=${encodeURIComponent(q)}&k=20`);
  const rows = data.results || [];
  $('results').innerHTML = rows.length ? rows.map(memoryCard).join('') : '<div class=\"empty\">No match</div>';
  $('stamp').textContent = `search latency ${data.latency_ms ?? '?'}ms`;
}

$('searchBtn').addEventListener('click', searchNow);
$('q').addEventListener('keydown', (ev) => {
  if (ev.key === 'Enter') searchNow();
});
$('distillBtn').addEventListener('click', async () => {
  await getJson('/api/distill?days=7', { method: 'POST' });
  await refreshSnapshot();
});
$('pollDueBtn').addEventListener('click', async () => {
  await getJson('/api/commitments/poll?limit=100', { method: 'POST' });
  await refreshSnapshot();
});

refreshSnapshot();
</script>
</body>
</html>
"""


class _DashboardHandler(BaseHTTPRequestHandler):
    root: Path

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(_dashboard_html())
            return

        if parsed.path == "/api/snapshot":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["200"])[0])
            self._send_json(build_dashboard_snapshot(self.root, limit=max(1, min(limit, 1000))))
            return

        if parsed.path == "/api/search":
            qs = parse_qs(parsed.query)
            q = (qs.get("q", [""])[0] or "").strip()
            k = int(qs.get("k", ["20"])[0])
            self._send_json(memory_search(query=q, k=max(1, min(k, 50)), root=self.root))
            return

        if parsed.path == "/api/memory":
            qs = parse_qs(parsed.query)
            mid = (qs.get("id", [""])[0] or "").strip()
            result = memory_get(mid, root=self.root)
            if result is None:
                self._send_json({"not_found": True, "id": mid}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(result)
            return

        if parsed.path == "/api/sessions":
            self._send_json({"sessions": _list_sessions(self.root)})
            return

        if parsed.path == "/api/commitments":
            qs = parse_qs(parsed.query)
            status = (qs.get("status", [""])[0] or "").strip() or None
            limit = int(qs.get("limit", ["200"])[0])
            self._send_json(reminder_status(root=self.root, status=status, limit=max(1, min(limit, 1000))))
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/distill":
            qs = parse_qs(parsed.query)
            days = int(qs.get("days", ["7"])[0])
            self._send_json(memory_distill(root=self.root, days=max(1, min(days, 365))))
            return

        if parsed.path == "/api/commitments/poll":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["100"])[0])
            self._send_json(reminder_poll(root=self.root, limit=max(1, min(limit, 1000))))
            return

        if parsed.path == "/api/commitments/complete":
            qs = parse_qs(parsed.query)
            reminder_id = (qs.get("id", [""])[0] or "").strip()
            note = (qs.get("note", [""])[0] or "").strip() or None
            self._send_json(reminder_complete(reminder_id=reminder_id, root=self.root, note=note))
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def run_dashboard_server(root: str | Path = "memory", host: str = "127.0.0.1", port: int = 8787) -> None:
    root_path = Path(root)

    class Handler(_DashboardHandler):
        root = root_path

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ClawMemory dashboard running on http://{host}:{port} (root={root_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
