---
name: agent-forge
description: Build or repair task agents from a user's working method: interview, create an executable playbook and indexed toolbox, configure bounded execution or requested automation, and verify results. Use for explicit agent-building, agent automation, delegation or Agent Forge project changes. Do not turn ordinary task requests or incidental mentions of agents into a building interview.
license: MIT
metadata:
  version: "0.2.0"
---

# Agent Forge

Turn work the user understands into a usable agent package, then improve it from observed results. The operating cycle is **playbook → run → check → fix → update playbook → rerun affected checks**. A skill file supplies instructions, not permanent background execution or unlimited authority.

## 1. Find the project and the real capabilities

Start from the supplied task, outcome, audience, examples, procedures, files, templates, integrations, constraints, authority, timing and quality expectations. For existing Agent Forge work, locate and read its playbook, configuration, toolbox and relevant run records before asking settled questions or creating duplicates. Preserve user edits and current project policies. Inspect existing checkpoints, queues and schedulers before creating state; use authoritative stores or indexed references rather than cloning them.

Discover available resources/tools before asking for information they may contain. Minimum capabilities: artifact reading/writing, resource search and a way to validate the intended outcome. Conditional: code execution, domain connectors, delegation, durable state, scheduler/event integration. Record required versus optional support, actual observations, setup and missing capabilities. Read [Codex support](references/codex.md) for that host; keep host-specific calls out of the task method. Verify other hosts on their own evidence.

## 2. Elicit the method, one consequential decision at a time

Resolve only material gaps. Establish trigger and inputs; how the user works, judgment rules and exceptions; acceptable and unacceptable examples; observable done; independent decisions, authority and escalation. Ask one consequential decision per turn. Use concrete contrasting examples to expose ambiguity. Do not assume that a task being recurring means scheduling is requested.

Always establish execution intent: **manual, one-time scheduled/queued, recurring, or event-triggered**. Reuse an explicit answer. When absent, ask at the appropriate interview point; leave mode unset in a draft. For automation settle trigger, timezone where relevant, dependencies/order, overlap, retries, stopping conditions and notifications.

Teach back the proposed procedure and work a representative example/dry run. Probe a difficult branch when useful. Readiness requires explicit steps, adequate examples, outcome checks, available prerequisites and escalation rules; it does not mean every possible case is learned. An unresolved consequential judgment or required capability blocks affected execution. Respect "draft now," "skip" and "use your judgment": record assumptions; deliver a draft or choose routine defaults within authority. Never turn those phrases into missing permission or invented domain facts. Keep private interview notes outside the reusable skill source.

## 3. Assemble the actual package

Create task projects outside this reusable folder, or extend the existing project in place. Deliver instructions, playbook, indexed toolbox, execution configuration and a supported invocation. Use [project contracts](references/contracts.md) and the bundled templates:

- [AGENT.md](templates/AGENT.md): runner and review cycle.
- [PLAYBOOK.md](templates/PLAYBOOK.md): task operating source of truth, including exact inputs/outputs, procedure/decisions, examples/exceptions, tools, permissions, completion checks/evidence, execution, limits/recovery and validated history.
- [agent.json](templates/agent.json): proposed bounds, observed capabilities, current authority and requested versus registered execution.
- [toolbox index](templates/toolbox-index.json): every durable resource or explicit storage reference.
- [run/review record](templates/run-review.json): frozen criteria, execution, observations, repair, regressions and uncertainty.

With Python 3.9+, `scripts/forge.py init NEW_PATH --project-id task-slug` scaffolds a **draft** and refuses any existing destination. The helper is optional, uses only the standard library and does not launch tasks or jobs. `find PROJECT --query TEXT` searches the index; `audit PROJECT` checks structure/inventory and any declared freshness bindings; `audit PROJECT --ready` adds readiness checks. Audit cannot prove task quality or actual authorization. For local source/evidence files whose byte identity matters, record an optional SHA-256 binding as described in [project contracts](references/contracts.md); audit checks only files explicitly pinned this way. A matching hash does not prove that the pinned source is authoritative or current. External references still need independent current-version/readback and outcome checks. Without Python, create equivalent artifacts manually and inspect the contracts; report unexecuted helper checks.

Before creating **each** durable file, script, template or document, search the toolbox and inspect relevant matches. Reuse or adapt a suitable item. Record why a new version/replacement is necessary if unsuitable; retain provenance and preserve customizations. "Never make the same thing again" means mandatory search and reuse, with justified regeneration still possible. Keep reusable templates distinct from individual outputs. Every durable asset—including task outputs, evidence and review records—needs purpose, location, version, contracts where relevant, dependencies, validation status and linked step/check IDs. Mark draft versus validated. External locations need explicit references and access/version checks. Credentials stay outside the toolbox. Define temporary/log retention; do not quietly classify durable outputs as disposable.

## 4. Freeze checks, configure limits, then run within scope

Define outcome checks **before** execution against source facts, user examples or another suitable independent oracle. Following the playbook alone is insufficient. Snapshot criterion IDs, expected results, methods and versions in the run record; candidate outputs must not control their own acceptance. Before delivery inspect every check entry for `id`, `expected`, `method`, `status`, `evidence` and `observed`, with genuine evidence for passing required checks; a separate successful checker does not fill omitted review fields. Establish a domain review method and critical failures. Run a representative case once sufficiently specified and execution is requested/authorized; otherwise deliver the usable package as prepared, not launched.

Propose task-appropriate finite limits. Starter values: three total attempts, 30 minutes shared effort, depth 1, concurrency 2, two workers total. Honor explicit zero delegation limits; unknown cost remains unknown and does not authorize paid tools. Each repair/child consumes the same parent budget. Stop earlier on repeated identical failures, a blocker, budget exhaustion, uncertain side effects or inability to verify. Define recovery and a next action.

For useful supported delegation, give each child a bounded objective, inputs, outputs, tools, authority, allowed files, owner, shared depth/concurrency/worker/retry/effort limits and fixed acceptance checks. Prevent conflicting writes; one owner per shared artifact. Parent integrates and independently reviews returns. No child may reset limits, expand permission or recursively spawn beyond the agreed depth. A zero depth/concurrency/worker bound disables delegation. Nested improvement loops need distinct checks/subtasks and the same total effort cap. Without orchestration, execute serially if authorized or deliver bounded handoffs and label them unlaunched.

Before processing a run, inspect existing run keys, active ownership and uncertain prior outcomes. Use supported queue leases/idempotency interfaces when available. Files alone cannot enforce concurrency. Without locking/deduplication support, require a single active writer and disclose that overlapping unattended execution is unsupported. Reconcile uncertain external actions using provider readback before retry; if unavailable, stop that action and preserve the reconciliation prerequisite.

## 5. Review, repair, learn and deliver

Check every applicable completion criterion and record actual evidence and failures/unknowns. Diagnose failures, repair affected work, then update the playbook/toolbox only for an evidence-supported reusable correction. Record failure → cause → correction → verification, changed versions and relevant regressions. When a reusable lesson applies, actually save it in the operating PLAYBOOK.md or affected toolbox resource and verify the saved version/diff; a lesson written only in a review record is not an updated playbook. If no existing playbook is available, create the task's learning artifact or explicitly mark this part of the cycle pending. Rerun affected checks and regression cases after the saved correction. Never rewrite criteria to make a failed result pass or silently expand authority. Required unavailable checks block a completed claim. Label outcomes passed, partial, failed, blocked or uncertain accurately.

For automation, inspect existing registrations/queues first and use supported host tools only within current authorization. Reconcile uncertain registration results before retrying. Verify actual registration by provider identifier, readback status, time and evidence; a schedule/queue file is **unregistered configuration** until then. Missing scheduler access means deliver configuration plus the exact missing capability, not an invented job. Check notification/overlap/dependency/stop behavior through supported evidence; do not claim unattended recurrence tested from one registration.

Deliver the result or package location, invocation, checked criteria/evidence, remaining limitations, actual launch/registration status and next action. If checks fail within bounds, deliver a labeled partial/failure report with usable work and recovery. Keep project lessons in the task playbook; record proposed reusable Agent Forge changes separately and validate them before incorporation. No model weights or unrelated-chat memory are changed. [Examples](references/examples.md) show the expected boundaries and evidence labels.
