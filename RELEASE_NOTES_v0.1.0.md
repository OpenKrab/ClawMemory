## ClawMemory v0.1.0

Initial public release with OpenClaw plugin integration and full local-first memory stack.

### Highlights
- OpenClaw memory plugin binding (`kind: memory`)
- Core tools: `memory_write`, `memory_search`, `memory_get`
- Session memory: `memory_session_append`, `memory_session_peek`, `memory_session_flush`
- Distillation: `memory_distill` updates `memory/MEMORY.md` and `memory/profile.md`
- Dashboard UI: timeline/search/health/session monitor
- Intent scheduler tools:
  - `memory_reminder_set`
  - `memory_reminder_status`
  - `memory_reminder_complete`
  - `memory_reminder_snooze`
  - `memory_reminder_poll`

### Reliability
- Persistent local storage (Markdown + SQLite)
- Reminder states: `pending`, `overdue`, `completed`
- Event-loop watcher with restart-safe recovery from persisted state

### Testing
- Test suite passing (`11 passed`)

