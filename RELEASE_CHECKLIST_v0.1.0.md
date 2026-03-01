# Release Checklist v0.1.0

## Scope
- OpenClaw-native memory plugin scaffold
- Phase 1: core contract + write/search/get
- Phase 2: session buffer + flush + distill + prompt-ready recall snippets
- Phase 3: local dashboard UI (timeline/search/health/session monitor)
- Phase 4: intent-based reminder scheduler (pending/overdue/completed)

## Pre-release Validation
- [x] Unit/integration tests pass
  - Command: `pytest -q tests --capture=no`
- [x] OpenClaw bridge commands tested (`write/search/get/session/distill/reminders`)
- [x] Dashboard API smoke-tested (`/api/snapshot`, `/api/commitments`)
- [x] Plugin manifest and extension entry files present
  - `openclaw.plugin.json`
  - `package.json` (`openclaw.extensions`)
  - `index.js`

## Packaging / Metadata
- [x] Python package metadata present (`pyproject.toml`)
- [x] OpenClaw plugin config schema updated (`reminderDefaultSeconds` included)
- [x] Skill doc updated (`skills/clawmemory/SKILL.md`)
- [x] README updated with run/install instructions

## Release Steps
- [x] Commit all release files
- [x] Create annotated tag: `v0.1.0`
- [ ] Push branch and tags to GitHub
- [ ] Create GitHub Release with notes

## Post-release Verification
- [ ] Verify tag on GitHub (`v0.1.0`)
- [ ] Verify Release page assets/notes
- [ ] Fresh install dry run:
  - `openclaw plugins install --link /path/to/ClawMemory`
  - `openclaw plugins enable clawmemory`
  - set `plugins.slots.memory = "clawmemory"`
