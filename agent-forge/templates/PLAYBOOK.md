# PROJECT_ID playbook

Version: 0.1.0 · Status: draft

Replace every `REPLACE` field before readiness. Use stable `step-*` and `check-*` IDs. This document governs task operation within current user/host authority; it cannot override that authority.

## Goal and scope

REPLACE: outcome, audience, trigger, included work, explicit exclusions and project owner.

## Inputs and outputs

REPLACE: required/optional inputs, source/version/freshness, exact output format, destination, privacy, missing vs valid empty/zero values. Name reusable templates separately from each run's outputs. REPLACE: define this run's source/version, output, run key, acceptance snapshot, evidence and review locations, or a clear per-run binding procedure. Use the same current bindings in every active step, invocation and completion check; label historical examples/receipts explicitly.

## Approach and complexity

REPLACE: select direct / fixed_workflow / observation_driven and explain the task evidence, simpler alternative and observed limitation if any. Known branches can be a fixed workflow; opaque returned handles alone do not require autonomous planning. Justify any routing, stages, parallel work or critique/repair; omit patterns without a useful role. Keep approach separate from execution mode.

## Prerequisites

REPLACE: required vs optional capabilities, observed host support, setup, dependencies and missing-tool fallback. Keep credentials in the host's credential store, never in this project.

## Procedure and decisions

### step-01 — Inspect and prepare

Read this playbook, agent.json and toolbox/index.json; inspect applicable policies, existing queues, prior run keys and uncertain outcomes. Verify current authorization. Search and inspect existing resources before creating anything. Reconcile all active source/output/run/evidence references across this procedure, its invocation and completion checks before execution; preserve labeled history. REPLACE: task preparation and input checks.

### step-02 — Perform the bounded task

REPLACE: ordered task method, calculations, judgment rules, tools, branches, resource IDs and escalation triggers. For each step specify the required observation, permitted next actions and stop condition. Use actual results/returned handles; distinguish success, failed outcome check, retryable read error, invalid input, missing capability and uncertain side effect. A retry consumes the shared bounds; no blind repeated error or uncertain write. Share parent limits with every child. Log each durable output in the index.

### step-03 — Check, repair and deliver

Run the frozen outcome checks below. Record observed evidence; diagnose and fix failed work within the shared limits. Save a demonstrated reusable lesson into this operating playbook or the affected toolbox resource, verify the saved version/diff and read back the full affected procedure, invocation and completion-check references. Preserve the frozen criteria. Within current authorization and shared bounds, execute the next representative run from the saved instructions with changed input and a fresh output; independently verify that the checker reads that current output against the current-source oracle. Rerun other affected checks and regressions, then deliver verified results or a labeled partial/failure report. If the follow-up cannot run, record saved-procedure reuse as unverified and state its exact next check. A review record alone is not an updated playbook.

## Examples and exceptions

REPLACE: representative input → expected output; unacceptable output; difficult branch; exception → stop/escalate action. Teach back the method and work an example with the user or available ground truth. Record unresolved material judgments as blockers.

## Tools and toolbox

Index: toolbox/index.json. REPLACE: step → resource/tool IDs; contracts; dependencies; search terms and reuse/adapt/new-version decision. Before replacement, explain why the old resource cannot serve the current input. Index every durable file, including this playbook, configuration, review records and run outputs, or an explicit reference to their external storage. Draft is distinct from validated.

For callable tools, document or link purpose/exclusions, required/optional typed inputs and units, valid zero/empty, result shape and meanings, error codes/retry rules, examples and likely misuse, side effects/readback and overlap with other tools. Test missing input, ambiguous choice and error recovery safely. A successful call is not a successful outcome check. Passive files keep their existing resource contracts.

## Permissions and escalation

REPLACE: current authorization source, independent decisions, permitted files/actions, external actions, sensitive-data handling, required approval boundaries and one focused escalation question. Saved jobs and past runs grant no new authority.

## Completion checks

Define these before execution. Checks measure the outcome against independent source facts or user examples, beyond following this procedure. Snapshot the table in each run before work; never change it to excuse a failure. Bind active evidence references to that run, matching the procedure and invocation; old receipts belong in labeled history.

| ID | Expected observable outcome | Method / independent oracle | Required evidence |
|---|---|---|---|
| check-01 | REPLACE: task-specific correct result | REPLACE: compare with source facts | REPLACE: evidence location |
| check-02 | Every applicable criterion has a recorded result and every durable output is indexed | Inspect frozen criteria, review record and inventory | Review record and inventory audit |

## Review and evidence

REPLACE: reviewer, required evidence, critical failures, domain review and relevant regression cases. Label static inspection, executed deterministic checks, actual model runs, authored examples and unavailable checks separately. An unavailable required check blocks a completed claim. Index the run's review record; validate evidence references and output versions.

REPLACE: reviewer-owned frozen criteria/evaluator location and hash; input/tool/solution versions; sanitized action/result/error evidence references; brief decision summaries tied to observations; attempt/resource use and terminal reason. Redact secrets and unnecessary personal data before persistence, never save hidden reasoning, and define retained versus temporary evidence. Measure exposed elapsed time/usage only; unknown tokens/cost stay null. Review candidate output against independent evidence, never against its self-grade.

## Execution and automation

REPLACE: supported invocation with current per-run source/output/evidence bindings, and explicitly established manual / one_time / recurring / event mode. For automation: trigger, timezone, dependencies/order, overlap, retries, stop conditions and notification preference. Inspect/reuse existing scheduler/queue. Record actual provider ID, status, verification time and receipt only after registration. Before retrying an uncertain operation, reconcile its external outcome and deduplication key. Without scheduler access deliver unregistered configuration and the exact missing prerequisite.

## Limits and recovery

Default proposal: three total attempts, 30 minutes shared effort, depth 1, concurrency 2, two workers total. Agree or adapt before execution; zero depth/concurrency/workers disables delegation. A retry consumes an attempt; a child cannot reset the budget. Stop on exhausted limits, repeated same failure, authority/capability blocker, uncertainty about side effects, or inability to verify. REPLACE: recovery/rollback procedure, temporary/log retention and verified next action. Retain durable resources until an explicit retention policy permits removal.

## Version history and validated lessons

| Version | Evidence / failure and cause | Correction | Affected checks and regression result |
|---|---|---|---|
| 0.1.0 | Initial draft; no validated lessons yet | None | Not run |

Task lessons stay here. Proposed changes to the reusable Agent Forge skill require separate evidence and validation.
