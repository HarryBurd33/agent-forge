# Codex host adapter

Core instructions are host-independent. This adapter describes observed Codex support, not a guarantee that another account/device/session has identical capabilities.

## Historical observations — original 0.2.0 build

On the local desktop build host, artifact read/write, resource search, shell/Python, Git, web research, subagent launch and private checkpoint storage were available. Useful construction and independent execution/review subagents actually ran. Installed `codex-cli 0.164.0` help confirmed `exec`, `--cd`, `--sandbox workspace-write` and prompt/stdin input. At that original build stage, no separate CLI model run, scheduler registration or unattended task delivery had been performed. The 2026-11-08 observations below supersede those coverage limits. Scheduler and domain connector access must be checked in the actual task session. Shell/network/sandbox approvals still apply.

Codex skill metadata supports `agents/openai.yaml` with `interface.display_name`; this package uses Agent Forge. Documented skill discovery depends on approved install locations. Merely placing this reviewable folder in a workspace is not proof of native discovery. See [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Supported invocation floor

Without installation, ask this chat to read the complete local SKILL.md and follow it. Once a task project is prepared and execution authorized, ask the chat to read that project's AGENT.md, PLAYBOOK.md, configuration and index, verify readiness/current scope and perform the bounded run. This is a manual invocation, not a scheduled process.

The installed CLI's verified syntax for an authorized local project is:

```
codex exec --cd /absolute/path/to/task-project --sandbox workspace-write 'Read AGENT.md, PLAYBOOK.md, agent.json and toolbox/index.json. Verify current scope and readiness, then perform the authorized manual run. Check the frozen outcomes and record evidence; stop within bounds.'
```

Review the actual task, scope, project policies and CLI help on the execution device. Keep normal sandbox, approval and hook trust controls. The command inherits the user's configured model and capabilities; it does not install a model or integration. No API service setup is required by this skill. [Official noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) documents this execution mode. Syntax inspection is narrower evidence than an executed task through that CLI.

## Conditional integrations

Use connected domain tools when available. Discover them before asking for already accessible files or data. Do not encode service-specific tool names in portable playbooks; record the actual task adapter and tested contract.

Use subagents only when useful and supported, with explicit child scope, files, owner, shared budget and check criteria. The parent integrates and reviews. If absent, use serial execution within authority or return unlaunched bounded handoffs.

For schedules, queued runs, reminders or event work, discover the host's supported automation tool first; inspect existing registrations/queues. Use the actual tool schema, verify registration ID/status/readback and distinguish requested, registered, paused, failed and uncertain states. A local JSON file never registers a job. Do not replace a missing integration with a new daemon or cron service implicitly. Recurrence/event delivery requires separate observed execution evidence.

Reuse an existing checkpoint/queue when compatible. A supported checkpoint integration is optional; do not bundle or require task-checkpoint. Without a durable lease or idempotency adapter, restrict execution to a single active writer and disclose the lack of overlapping unattended support. On resume recheck current user authority, jobs and external side effects; saved configuration cannot supply permission.
## Additional host observations — 2026-11-08

CLI0.166.0 was actually invoked in fresh ephemeral contexts using managed ChatGPT sign-in, normal workspace sandbox/rules/hook trust, explicit Sol/Medium, and no API-key fallback. Literal `$agent-forge` discovery/loading and a small local execution passed; a separate ordinary-task exclusion passed. This is native CLI evidence on one host, not every desktop picker/device or model build.

The native host tool registered a finite timer pilot; two distinct later receiving turns produced correct local outputs and the exact schedule was deleted before the second output. The first delivery was delayed, so this establishes two bounded deliveries and cleanup, not exact cadence or indefinite reliability. The [current scheduled-task documentation](https://learn.chatgpt.com/docs/automations) says supported app-event tasks require an eligible web/mobile host and app connection; they are unavailable in desktop/CLI/IDE. Do not substitute a timer, manual call or local config for event delivery. Prepare the event contract and name that exact host prerequisite. Changing model defaults or starting an extra daemon is not a remedy for missing host support.
