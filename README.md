# ClawMemory

Starter implementation for **Phase 4: Intent-Based Scheduler + Dashboard**.
Now includes **OpenClaw-native plugin binding** for `memory` slot.

## What is included

- Memory contract with required metadata: `id`, `source`, `timestamp`, `tags`, `confidence`
- Local-first storage:
  - Markdown source of truth in `memory/events/*.md`
  - SQLite index in `memory/index.sqlite3`
  - Curated summary in `memory/MEMORY.md`
  - Stable profile in `memory/profile.md`
- Core tools:
  - `memory_write(payload)`
  - `memory_search(query, k)` (hybrid keyword + semantic + snippet + prompt context)
  - `memory_get(id)` with provenance
- Short-term memory:
  - session buffer append/peek/flush
  - auto-flush threshold
- Safe auto-capture extractor with confidence threshold
- Weekly distill (`events -> MEMORY.md` + `profile.md`)
- Local dashboard UI:
  - memory browser timeline
  - search and snippet recall
  - top source/tag health cards
  - session buffer monitor
  - one-click weekly distill trigger
- Intent-based reminder scheduler:
  - persistent commitments (`pending/overdue/completed`)
  - event-loop watcher with recovery after restart
  - due polling (no fixed cron dependency)
- Claw ecosystem integrations:
  - ClawReceipt recurring finance pattern capture (`finance/recurring`)
  - ClawFlow cron setup memory + fail follow-up reminder
  - ClawWizard preference mode memory (`interactive` vs `cli`)
- Semantic backend options (local-only):
  - default lightweight hashed embedding
  - optional real local vector backend (`chroma` + sentence-transformers)
- Baseline test coverage

## Project layout

- `clawmemory/contract.py` - memory schema and payload validation
- `clawmemory/store.py` - markdown + sqlite index + hybrid retrieval + dedup
- `clawmemory/tools.py` - public tool functions
- `clawmemory/autocapture.py` - reusable-fact extractor
- `clawmemory/session_buffer.py` - short-term session buffer + flush
- `clawmemory/distill.py` - weekly curated + profile distill
- `clawmemory/metrics.py` - precision/latency/duplicate/growth helpers
- `clawmemory/commitments.py` - persistent intent scheduler engine
- `clawmemory/integrations.py` - ClawReceipt/ClawFlow/ClawWizard capture helpers
- `clawmemory/vector_semantic.py` - semantic backend abstraction (hashed/chroma)
- `clawmemory/cli.py` - command line entrypoint
- `clawmemory/dashboard.py` - local web server + UI + API endpoints
- `ui/clawmemory-next/` - Next.js + shadcn-style dashboard scaffold

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## OpenClaw plugin binding

This repo now exposes an OpenClaw plugin with:

- `openclaw.plugin.json` (`id: clawmemory`, `kind: memory`)
- `package.json` with `openclaw.extensions = ["./index.js"]`
- `index.js` registering:
  - `memory_write`
  - `memory_search`
  - `memory_get`
  - `memory_session_append`
  - `memory_session_peek`
  - `memory_session_flush`
  - `memory_distill`
  - `memory_reminder_set`
  - `memory_reminder_status`
  - `memory_reminder_complete`
  - `memory_reminder_snooze`
  - `memory_reminder_poll`
  - `clawreceipt_capture_patterns`
  - `clawflow_capture_cron_setup`
  - `clawflow_capture_job_failure`
  - `clawwizard_set_preference_mode`

The OpenClaw plugin calls the Python backend through:

- `python -m clawmemory.openclaw_bridge`

### Install into OpenClaw

```bash
openclaw plugins install --link /absolute/path/to/ClawMemory
openclaw plugins enable clawmemory
```

Set memory slot to this plugin in OpenClaw config:

```json
{
  "plugins": {
    "slots": {
      "memory": "clawmemory"
    }
  }
}
```

Optional plugin config:

- `pythonBin` (default: `python3`)
- `memoryRoot` (default: `memory`)
- `timeoutMs` (default: `20000`)
- `autoFlushMaxTurns` (default: `24`)
- `minConfidence` (default: `0.7`)
- `reminderDefaultSeconds` (default: `300`)
- `vectorBackend` (`hashed` default, set `chroma` for real local vector DB)
- `embedModel` (`all-MiniLM-L6-v2` default for chroma backend)

Write one memory:

```bash
clawmemory write --payload '{"text":"User prefers interactive wizard over CLI.","source":"clawwizard/session","tags":["preference"],"confidence":0.9}'
```

Search memories:

```bash
clawmemory search --query "wizard preference" -k 5
```

Get memory:

```bash
clawmemory get --id <memory_id>
```

Auto-capture + write:

```bash
clawmemory autocapture --conversation examples/conversation.json --min-confidence 0.7 --write
```

Weekly distill:

```bash
clawmemory distill --days 7
```

Session buffer append/peek/flush:

```bash
clawmemory session-append --session-id s1 --role user --content "I prefer wizard setup"
clawmemory session-peek --session-id s1 --limit 20
clawmemory session-flush --session-id s1 --min-confidence 0.7
```

Run dashboard UI:

```bash
clawmemory dashboard --host 127.0.0.1 --port 8787
```

Then open:

```text
http://127.0.0.1:8787
```

Next.js dashboard scaffold (optional):

```bash
cd ui/clawmemory-next
npm install
npm run dev
```

Set API base:

```bash
NEXT_PUBLIC_CLAWMEMORY_API_BASE=http://127.0.0.1:8787 npm run dev
```

Reminder commands:

```bash
clawmemory reminder-set --text "check build result" --in-seconds 300
clawmemory reminder-list --status pending
clawmemory reminder-poll --limit 100
clawmemory reminder-complete --id <reminder_id> --note "done"
clawmemory reminder-snooze --id <reminder_id> --seconds 120
```

Run event-loop watcher:

```bash
clawmemory reminder-watch --interval 1.0 --max-sleep 30
```

Integration examples:

```bash
# ClawReceipt recurring pattern capture
python -m clawmemory.openclaw_bridge integration_capture_receipts --root memory <<'JSON'
{"events":[{"merchant":"Shopee","amount":500,"timestamp":"2026-01-25T10:00:00+00:00"},{"merchant":"Shopee","amount":700,"timestamp":"2026-02-26T10:00:00+00:00"}]}
JSON

# ClawFlow cron setup memory
python -m clawmemory.openclaw_bridge integration_flow_cron_setup --root memory <<'JSON'
{"cron_expression":"0 9 * * *","job_name":"daily-report"}
JSON

# ClawWizard preference memory
python -m clawmemory.openclaw_bridge integration_wizard_preference --root memory <<'JSON'
{"mode":"interactive"}
JSON
```

## Notes

- Privacy/self-host focus: no cloud API is required by default.
- For stronger semantic retrieval, enable real local backend:
  - `pip install -e .[vector]`
  - `export CLAWMEMORY_VECTOR_BACKEND=chroma`
  - optional: `export CLAWMEMORY_EMBED_MODEL=all-MiniLM-L6-v2`
