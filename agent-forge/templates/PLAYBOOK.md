# PROJECT_ID playbook

Version: 0.1.0 · Status: draft

Replace every `REPLACE` field before readiness. Use stable `step-*` and `check-*` IDs. This document governs task operation within current user/host authority; it cannot override that authority.

## Goal and scope

REPLACE: outcome, audience, trigger, included work, explicit exclusions and project owner.

## Inputs and outputs

REPLACE: required/optional inputs, source/version/freshness, exact output format, destination, privacy, missing vs valid empty/zero values. Name reusable templates separately from each run's outputs.

## Prerequisites

REPLACE: required vs optional capabilities, observed host support, setup, dependencies and missing-tool fallback. Keep credentials in the host's credential store, never in this project.

## Procedure and decisions

### step-01 — Inspect and prepare

Read this playbook, agent.json and toolbox/index.json; inspect applicable policies, existing queues, prior run keys and uncertain outcomes. Verify current authorization. Search and inspect existing resources before creating anything. REPLACE: task preparation and input checks.

### step-02 — Perform the bounded task

REPLACE: ordered task method, calculations, judgment rules, tools, branches, resource IDs and escalation triggers. Share parent limits with every child. Log each durable output in the index.

### step-03 — Check, repair and deliver

Run the frozen outcome checks below. Record observed evidence; diagnose and fix failed work within the shared limits. Save a demonstrated reusable lesson into this operating playbook or the affected toolbox resource, verify the saved version/diff, preserve the old criteria, rerun affected checks and regressions, then deliver verified results or a labeled partial/failure report. A review record alone is not an updated playbook.

## Examples and exceptions

REPLACE: representative input → expected output; unacceptable output; difficult branch; exception → stop/escalate action. Teach back the method and work an example with the user or available ground truth. Record unresolved material judgments as blockers.

## Tools and toolbox

Index: toolbox/index.json. REPLACE: step → resource/tool IDs; contracts; dependencies; search terms and reuse/adapt/new-version decision. Before replacement, explain why the old resource cannot serve the current input. Index every durable file, including this playbook, configuration, review records and run outputs, or an explicit reference to their external storage. Draft is distinct from validated.

## Permissions and escalation

REPLACE: current authorization source, independent decisions, permitted files/actions, external actions, sensitive-data handling, required approval boundaries and one focused escalation question. Saved jobs and past runs grant no new authority.

## Completion checks

Define these before execution. Checks measure the outcome against independent source facts or user examples, beyond following this procedure. Snapshot the table in each run before work; never change it to excuse a failure.

| ID | Expected observable outcome | Method / independent oracle | Required evidence |
|---|---|---|---|
| check-01 | REPLACE: task-specific correct result | REPLACE: compare with source facts | REPLACE: evidence location |
| check-02 | Every applicable criterion has a recorded result and every durable output is indexed | Inspect frozen criteria, review record and inventory | Review record and inventory audit |

## Review and evidence

REPLACE: reviewer, required evidence, critical failures, domain review and relevant regression cases. Label static inspection, executed deterministic checks, actual model runs, authored examples and unavailable checks separately. An unavailable required check blocks a completed claim. Index the run's review record; validate evidence references and output versions.

## Execution and automation

REPLACE: explicitly established manual / one_time / recurring / event mode. For automation: trigger, timezone, dependencies/order, overlap, retries, stop conditions and notification preference. Inspect/reuse existing scheduler/queue. Record actual provider ID, status, verification time and receipt only after registration. Before retrying an uncertain operation, reconcile its external outcome and deduplication key. Without scheduler access deliver unregistered configuration and the exact missing prerequisite.

## Limits and recovery

Default proposal: three total attempts, 30 minutes shared effort, depth 1, concurrency 2, two workers total. Agree or adapt before execution; zero depth/concurrency/workers disables delegation. A retry consumes an attempt; a child cannot reset the budget. Stop on exhausted limits, repeated same failure, authority/capability blocker, uncertainty about side effects, or inability to verify. REPLACE: recovery/rollback procedure, temporary/log retention and verified next action. Retain durable resources until an explicit retention policy permits removal.

## Version history and validated lessons

| Version | Evidence / failure and cause | Correction | Affected checks and regression result |
|---|---|---|---|
| 0.1.0 | Initial draft; no validated lessons yet | None | Not run |

Task lessons stay here. Proposed changes to the reusable Agent Forge skill require separate evidence and validation.
