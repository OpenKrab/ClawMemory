## ClawMemory v0.1.0

Initial public release with OpenClaw plugin integration and full local-first memory stack.

### Highlights
- OpenClaw memory plugin binding (`kind: memory`)
- Core tools: `memory_write`, `memory_search`, `memory_get`
- Session memory: `memory_session_append`, `memory_session_peek`, `memory_session_flush`
- Distillation: `memory_distill` updates `memory/MEMORY.md` and `memory/profile.md`
- Dashboard UI: timeline/search/health/session monitor
- Virtual office visualization (filing cabinet interaction on memory update)
- Claw ecosystem integrations:
  - `clawreceipt_capture_patterns` (auto-tag `finance/recurring`)
  - `clawflow_capture_cron_setup`
  - `clawflow_capture_job_failure` (auto reminder)
  - `clawwizard_set_preference_mode`
- Intent scheduler tools:
  - `memory_reminder_set`
  - `memory_reminder_status`
  - `memory_reminder_complete`
  - `memory_reminder_snooze`
  - `memory_reminder_poll`
- Optional real local semantic backend:
  - `CLAWMEMORY_VECTOR_BACKEND=chroma`
  - local `sentence-transformers` embeddings (no cloud required)
- Next.js + shadcn-style dashboard scaffold under `ui/clawmemory-next`

### Reliability
- Persistent local storage (Markdown + SQLite)
- Reminder states: `pending`, `overdue`, `completed`
- Event-loop watcher with restart-safe recovery from persisted state

### Testing
- Test suite passing (`13 passed`)
