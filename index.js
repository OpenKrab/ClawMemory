import { spawnSync } from "node:child_process";

function asObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value;
}

function normalizeConfig(api) {
  const cfg = asObject(api.pluginConfig);
  const pythonBin =
    typeof cfg.pythonBin === "string" && cfg.pythonBin.trim()
      ? cfg.pythonBin.trim()
      : "python3";
  const memoryRootInput =
    typeof cfg.memoryRoot === "string" && cfg.memoryRoot.trim()
      ? cfg.memoryRoot.trim()
      : "memory";
  const timeoutMsRaw =
    typeof cfg.timeoutMs === "number" ? cfg.timeoutMs : 20000;
  const timeoutMs =
    Number.isFinite(timeoutMsRaw) && timeoutMsRaw > 0
      ? Math.floor(timeoutMsRaw)
      : 20000;
  const autoFlushMaxTurnsRaw =
    typeof cfg.autoFlushMaxTurns === "number" ? cfg.autoFlushMaxTurns : 24;
  const autoFlushMaxTurns = Number.isFinite(autoFlushMaxTurnsRaw)
    ? Math.max(0, Math.floor(autoFlushMaxTurnsRaw))
    : 24;
  const minConfidenceRaw =
    typeof cfg.minConfidence === "number" ? cfg.minConfidence : 0.7;
  const minConfidence = Number.isFinite(minConfidenceRaw)
    ? Math.max(0, Math.min(1, minConfidenceRaw))
    : 0.7;
  const reminderDefaultSecondsRaw =
    typeof cfg.reminderDefaultSeconds === "number"
      ? cfg.reminderDefaultSeconds
      : 300;
  const reminderDefaultSeconds = Number.isFinite(reminderDefaultSecondsRaw)
    ? Math.max(1, Math.floor(reminderDefaultSecondsRaw))
    : 300;
  const vectorBackend =
    typeof cfg.vectorBackend === "string" && cfg.vectorBackend.trim()
      ? cfg.vectorBackend.trim().toLowerCase()
      : "hashed";
  const embedModel =
    typeof cfg.embedModel === "string" && cfg.embedModel.trim()
      ? cfg.embedModel.trim()
      : "all-MiniLM-L6-v2";

  return {
    pythonBin,
    memoryRoot: api.resolvePath(memoryRootInput),
    timeoutMs,
    autoFlushMaxTurns,
    minConfidence,
    reminderDefaultSeconds,
    vectorBackend,
    embedModel,
  };
}

function textResult(text, details = {}) {
  return {
    content: [{ type: "text", text }],
    details,
  };
}

function runBridge({
  pythonBin,
  memoryRoot,
  timeoutMs,
  command,
  payload,
  vectorBackend,
  embedModel,
}) {
  const proc = spawnSync(
    pythonBin,
    ["-m", "clawmemory.openclaw_bridge", command, "--root", memoryRoot],
    {
      input: JSON.stringify(payload ?? {}),
      encoding: "utf-8",
      timeout: timeoutMs,
      env: {
        ...process.env,
        CLAWMEMORY_VECTOR_BACKEND:
          vectorBackend || process.env.CLAWMEMORY_VECTOR_BACKEND || "hashed",
        CLAWMEMORY_EMBED_MODEL:
          embedModel ||
          process.env.CLAWMEMORY_EMBED_MODEL ||
          "all-MiniLM-L6-v2",
      },
    },
  );

  if (proc.error) {
    throw new Error(`clawmemory bridge failed to start: ${String(proc.error)}`);
  }
  if (proc.status !== 0) {
    const stderr = (proc.stderr || "").trim();
    const stdout = (proc.stdout || "").trim();
    throw new Error(
      `clawmemory bridge error (exit ${proc.status}): ${stderr || stdout || "unknown error"}`,
    );
  }

  const raw = (proc.stdout || "").trim();
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(
      `clawmemory bridge invalid JSON output: ${String(err)}; raw=${raw.slice(0, 400)}`,
    );
  }
}

const plugin = {
  id: "clawmemory",
  name: "ClawMemory",
  description:
    "Local-first memory plugin with session buffer, hybrid recall, and weekly distill",
  kind: "memory",
  register(api) {
    const cfg = normalizeConfig(api);
    api.logger.info(
      `clawmemory: registered (root=${cfg.memoryRoot}, python=${cfg.pythonBin})`,
    );

    api.registerTool(
      {
        name: "memory_write",
        label: "Memory Write",
        description:
          "Write a memory entry with deduplication into ClawMemory store.",
        parameters: {
          type: "object",
          properties: {
            text: { type: "string", description: "Memory text" },
            source: {
              type: "string",
              description: "Source label, e.g. clawwizard/session",
            },
            tags: { type: "array", items: { type: "string" } },
            confidence: { type: "number" },
            metadata: { type: "object" },
          },
          required: ["text", "source"],
        },
        async execute(_toolCallId, params) {
          const res = runBridge({
            ...cfg,
            command: "write",
            payload: asObject(params),
          });
          return textResult(
            `memory_write: ${res.status || "ok"} (${res.id || "n/a"})`,
            res,
          );
        },
      },
      { name: "memory_write" },
    );

    api.registerTool(
      {
        name: "memory_search",
        label: "Memory Search",
        description:
          "Search memories using hybrid semantic + lexical scoring and prompt-ready snippets.",
        parameters: {
          type: "object",
          properties: {
            query: { type: "string", description: "Search query" },
            k: { type: "number", description: "Top-k results (default 5)" },
          },
          required: ["query"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "search",
            payload: {
              query: typeof p.query === "string" ? p.query : "",
              k: typeof p.k === "number" ? p.k : 5,
            },
          });
          const count = Array.isArray(res.results) ? res.results.length : 0;
          return textResult(`memory_search: found ${count} result(s)`, res);
        },
      },
      { name: "memory_search" },
    );

    api.registerTool(
      {
        name: "memory_get",
        label: "Memory Get",
        description: "Retrieve one memory by id with provenance.",
        parameters: {
          type: "object",
          properties: {
            id: { type: "string", description: "Memory entry id" },
          },
          required: ["id"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "get",
            payload: { id: typeof p.id === "string" ? p.id : "" },
          });
          const state = res && !res.not_found ? "ok" : "not_found";
          return textResult(`memory_get: ${state}`, res);
        },
      },
      { name: "memory_get" },
    );

    api.registerTool(
      {
        name: "memory_session_append",
        label: "Memory Session Append",
        description:
          "Append one conversation turn to short-term session buffer. Auto-flush when threshold is reached.",
        parameters: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            role: { type: "string", enum: ["user", "assistant", "system"] },
            content: { type: "string" },
            auto_flush_max_turns: { type: "number" },
            min_confidence: { type: "number" },
          },
          required: ["session_id", "role", "content"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "session_append",
            payload: {
              session_id: String(p.session_id || "").trim(),
              role: String(p.role || "user").trim() || "user",
              content: String(p.content || "").trim(),
              auto_flush_max_turns:
                typeof p.auto_flush_max_turns === "number"
                  ? p.auto_flush_max_turns
                  : cfg.autoFlushMaxTurns,
              min_confidence:
                typeof p.min_confidence === "number"
                  ? p.min_confidence
                  : cfg.minConfidence,
            },
          });
          return textResult(
            `memory_session_append: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "memory_session_append" },
    );

    api.registerTool(
      {
        name: "memory_session_peek",
        label: "Memory Session Peek",
        description: "Read short-term session buffer turns.",
        parameters: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            limit: { type: "number" },
          },
          required: ["session_id"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "session_peek",
            payload: {
              session_id: String(p.session_id || "").trim(),
              limit: typeof p.limit === "number" ? Math.floor(p.limit) : null,
            },
          });
          return textResult(
            `memory_session_peek: ${res.count || 0} turn(s)`,
            res,
          );
        },
      },
      { name: "memory_session_peek" },
    );

    api.registerTool(
      {
        name: "memory_session_flush",
        label: "Memory Session Flush",
        description:
          "Extract reusable facts from session buffer and store them in long-term memory.",
        parameters: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            min_confidence: { type: "number" },
            keep_buffer: { type: "boolean" },
          },
          required: ["session_id"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "session_flush",
            payload: {
              session_id: String(p.session_id || "").trim(),
              min_confidence:
                typeof p.min_confidence === "number"
                  ? p.min_confidence
                  : cfg.minConfidence,
              keep_buffer: Boolean(p.keep_buffer),
            },
          });
          return textResult(`memory_session_flush: ${res.status || "ok"}`, res);
        },
      },
      { name: "memory_session_flush" },
    );

    api.registerTool(
      {
        name: "memory_distill",
        label: "Memory Distill",
        description:
          "Distill recent memory entries into MEMORY.md and update profile.md.",
        parameters: {
          type: "object",
          properties: {
            days: { type: "number", description: "Lookback days (default: 7)" },
          },
          required: [],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "distill",
            payload: { days: typeof p.days === "number" ? p.days : 7 },
          });
          return textResult(`memory_distill: ${res.status || "ok"}`, res);
        },
      },
      { name: "memory_distill" },
    );

    api.registerTool(
      {
        name: "memory_reminder_set",
        label: "Memory Reminder Set",
        description:
          "Set a commitment/reminder with due time (intent-based scheduler, persistent).",
        parameters: {
          type: "object",
          properties: {
            text: { type: "string", description: "Reminder text" },
            due_in_seconds: {
              type: "number",
              description: "Due in seconds (default 300)",
            },
            due_at: { type: "string", description: "Absolute ISO due time" },
            session_id: { type: "string" },
            metadata: { type: "object" },
          },
          required: ["text"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "reminder_set",
            payload: {
              text: String(p.text || "").trim(),
              due_in_seconds:
                typeof p.due_in_seconds === "number"
                  ? Math.floor(p.due_in_seconds)
                  : cfg.reminderDefaultSeconds,
              due_at: typeof p.due_at === "string" ? p.due_at.trim() : "",
              session_id:
                typeof p.session_id === "string" ? p.session_id.trim() : "",
              metadata: asObject(p.metadata),
            },
          });
          return textResult(
            `memory_reminder_set: ${res.status || "ok"} (${res.id || "n/a"})`,
            res,
          );
        },
      },
      { name: "memory_reminder_set" },
    );

    api.registerTool(
      {
        name: "memory_reminder_status",
        label: "Memory Reminder Status",
        description:
          "List reminder status and health for pending/overdue/completed commitments.",
        parameters: {
          type: "object",
          properties: {
            status: {
              type: "string",
              description: "pending|overdue|completed or empty",
            },
            limit: { type: "number", description: "Max items (default 200)" },
          },
          required: [],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "reminder_status",
            payload: {
              status: typeof p.status === "string" ? p.status.trim() : "",
              limit: typeof p.limit === "number" ? Math.floor(p.limit) : 200,
            },
          });
          const count = Array.isArray(res.items) ? res.items.length : 0;
          return textResult(`memory_reminder_status: ${count} item(s)`, res);
        },
      },
      { name: "memory_reminder_status" },
    );

    api.registerTool(
      {
        name: "memory_reminder_complete",
        label: "Memory Reminder Complete",
        description: "Mark a reminder as completed.",
        parameters: {
          type: "object",
          properties: {
            id: { type: "string" },
            note: { type: "string" },
          },
          required: ["id"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "reminder_complete",
            payload: {
              id: typeof p.id === "string" ? p.id.trim() : "",
              note: typeof p.note === "string" ? p.note.trim() : "",
            },
          });
          return textResult(
            `memory_reminder_complete: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "memory_reminder_complete" },
    );

    api.registerTool(
      {
        name: "memory_reminder_snooze",
        label: "Memory Reminder Snooze",
        description: "Snooze reminder due time by N seconds.",
        parameters: {
          type: "object",
          properties: {
            id: { type: "string" },
            seconds: { type: "number" },
          },
          required: ["id", "seconds"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "reminder_snooze",
            payload: {
              id: typeof p.id === "string" ? p.id.trim() : "",
              seconds:
                typeof p.seconds === "number" ? Math.floor(p.seconds) : 60,
            },
          });
          return textResult(
            `memory_reminder_snooze: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "memory_reminder_snooze" },
    );

    api.registerTool(
      {
        name: "memory_reminder_poll",
        label: "Memory Reminder Poll",
        description: "Poll due reminders and promote them to overdue.",
        parameters: {
          type: "object",
          properties: {
            limit: { type: "number" },
          },
          required: [],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "reminder_poll",
            payload: {
              limit: typeof p.limit === "number" ? Math.floor(p.limit) : 50,
            },
          });
          return textResult(`memory_reminder_poll: ${res.count || 0} due`, res);
        },
      },
      { name: "memory_reminder_poll" },
    );

    api.registerTool(
      {
        name: "clawreceipt_capture_patterns",
        label: "ClawReceipt Capture Patterns",
        description:
          "Capture recurring finance patterns from receipt events and store as memory tags finance/recurring.",
        parameters: {
          type: "object",
          properties: {
            events: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  merchant: { type: "string" },
                  amount: { type: "number" },
                  timestamp: { type: "string" },
                },
              },
            },
          },
          required: ["events"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const events = Array.isArray(p.events) ? p.events : [];
          const res = runBridge({
            ...cfg,
            command: "integration_capture_receipts",
            payload: { events },
          });
          return textResult(
            `clawreceipt_capture_patterns: ${res.count || 0} pattern(s)`,
            res,
          );
        },
      },
      { name: "clawreceipt_capture_patterns" },
    );

    api.registerTool(
      {
        name: "clawflow_capture_cron_setup",
        label: "ClawFlow Capture Cron Setup",
        description: "Remember cron setup that was installed by ClawFlow.",
        parameters: {
          type: "object",
          properties: {
            cron_expression: { type: "string" },
            job_name: { type: "string" },
          },
          required: ["cron_expression", "job_name"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "integration_flow_cron_setup",
            payload: {
              cron_expression: String(p.cron_expression || "").trim(),
              job_name: String(p.job_name || "").trim(),
            },
          });
          return textResult(
            `clawflow_capture_cron_setup: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "clawflow_capture_cron_setup" },
    );

    api.registerTool(
      {
        name: "clawflow_capture_job_failure",
        label: "ClawFlow Capture Job Failure",
        description: "Record flow job failure and set reminder to follow up.",
        parameters: {
          type: "object",
          properties: {
            job_name: { type: "string" },
            fail_reason: { type: "string" },
            remind_in_seconds: { type: "number" },
          },
          required: ["job_name", "fail_reason"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "integration_flow_job_failure",
            payload: {
              job_name: String(p.job_name || "").trim(),
              fail_reason: String(p.fail_reason || "").trim(),
              remind_in_seconds:
                typeof p.remind_in_seconds === "number"
                  ? Math.floor(p.remind_in_seconds)
                  : 300,
            },
          });
          return textResult(
            `clawflow_capture_job_failure: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "clawflow_capture_job_failure" },
    );

    api.registerTool(
      {
        name: "clawwizard_set_preference_mode",
        label: "ClawWizard Set Preference Mode",
        description: "Store user wizard preference mode (interactive or cli).",
        parameters: {
          type: "object",
          properties: {
            mode: { type: "string", enum: ["interactive", "cli"] },
          },
          required: ["mode"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const res = runBridge({
            ...cfg,
            command: "integration_wizard_preference",
            payload: {
              mode: String(p.mode || "")
                .trim()
                .toLowerCase(),
            },
          });
          return textResult(
            `clawwizard_set_preference_mode: ${res.status || "ok"}`,
            res,
          );
        },
      },
      { name: "clawwizard_set_preference_mode" },
    );
    api.registerTool(
      {
        name: "clawgraph_sync_entities",
        label: "ClawGraph Sync Entities",
        description:
          "Sync projects, clients, tasks, expenses, and reminders for ClawGraph relationship mapping.",
        parameters: {
          type: "object",
          properties: {
            entities: {
              type: "object",
              properties: {
                projects: { type: "array", items: { type: "object" } },
                clients: { type: "array", items: { type: "object" } },
                tasks: { type: "array", items: { type: "object" } },
                expenses: { type: "array", items: { type: "object" } },
                reminders: { type: "array", items: { type: "object" } },
              },
            },
          },
          required: ["entities"],
        },
        async execute(_toolCallId, params) {
          const p = asObject(params);
          const entities = asObject(p.entities);
          const res = runBridge({
            ...cfg,
            command: "integration_graph_sync",
            payload: { entities },
          });
          return textResult(`clawgraph_sync_entities: synced`, res);
        },
      },
      { name: "clawgraph_sync_entities" },
    );
  },
};

export default plugin;
