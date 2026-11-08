# Project contracts, version 1

These are original local artifact contracts, not a scheduler, queue database, sandbox or autonomous runtime. Python helpers are optional; another host may edit equivalent files directly. A helper audit checks explicit structural rules, never arbitrary task quality, authorization or all secrets.

Version 0.3.0 retains version-1 project/index compatibility and the 0.2.0 opt-in freshness bindings. New approach and diagnostic fields are additive; old projects are not silently migrated. A direct prompt/tool solution may use a smaller deliverable instead of this full layout.

## Approach, tool interfaces and diagnostic events

Record approach (`direct`, `fixed_workflow`, or `observation_driven`), task-specific reason and simpler alternative in the playbook; the run template also has an optional `approach` summary. Do not confuse this with `execution.mode`. Choose optional patterns only when they serve the task, as described in [engineering decisions](engineering.md).

Callable resources keep their existing index entry and link to an inspected tool contract: purpose/exclusions, invocation, typed required/optional inputs/units/valid zero, result meaning, errors/retry policy, examples, effects/authority/readback, and ambiguity with other tools. This is not a second resource registry. Passive resources need no invented tool schema.

Optional `events` in a run record contain compact operational evidence, for example:

```json
{
  "step_id": "step-02",
  "tool": "read_rows",
  "input_refs": ["inputs/source.json"],
  "arguments_summary": {"dataset": "primary"},
  "observation": {"status": "error", "code": "E_TEMP", "evidence": ["runs/01/read-error.json"]},
  "decision_summary": "The read-only tool explicitly marked this error retryable; one retry remains.",
  "next_action": "retry read_rows once",
  "remaining_bounds": {"attempts": 1}
}
```

This is an authored example, not an observed run. Never store hidden reasoning, secrets or unnecessary identifying payloads. Sanitize before persistence; do not retain an unredacted secondary log. Preserve useful error codes, input/version references and evidence IDs. `terminal_reason` states why execution ended. Known solution/tool/model versions belong in `versions`; unavailable task tokens/cost stay null. The helper does not authenticate trace truth, model identity or enforce budgets.

## Optional run-record conformance check

```sh
python3 scripts/forge.py audit-run PROJECT --record runs/01/review.json --criteria /reviewer/criteria.json --criteria-sha256 EXPECTED_SHA256
```

The caller supplies a separately owned acceptance file and its independently recorded SHA-256. Its format is `{"checks":[{"id":"check-01","expected":0,"method":"Compare current source sum","required":true}]}`. Required defaults to true. Freeze this file and its evaluator before candidate execution, outside candidate write authority. A hash supplied by the same candidate is not independent control; the helper cannot enforce host access boundaries or authenticate the caller.

The record needs a valid run `status` and `checks`. Each check needs `id`, `expected`, `method`, `status`, `evidence`, `observed`. IDs must be unique and correspond to the supplied criteria; required IDs must be present. Expected values and methods must match the frozen criteria, including JSON types. Check statuses are `pass`, `fail`, `blocked`, `unavailable`, `not_run`, `not_applicable`; run statuses are `planned`, `running`, `passed`, `partial`, `failed`, `blocked`, `uncertain`. Passing checks require nonempty evidence references and a non-null observation; numeric zero and false are valid observations. Evidence paths must exist or be explicit supported external references. A `not_applicable` check requires a nonempty explanation string in `observed` and an independently frozen criterion with `required: false`; it cannot excuse a required check. A passed run requires all required checks to pass. Failed or blocked records can be structurally valid without being successful runs.

The command checks record conformance and a pinned snapshot, not whether evidence is true, the source authoritative, the chosen criteria sufficient, or an external action completed. It does not run an evaluator or fetch remote evidence. Existing `audit` remains a project/inventory check and does not imply `audit-run` passed. Use both when appropriate, then inspect actual outcome evidence independently.

## Layout and source of truth

`AGENT.md` is the runner; `PLAYBOOK.md` governs the task; `agent.json` records configuration; `toolbox/index.json` inventories every durable resource, including itself. Run records normally live at `runs/<run-id>/review.json`; outputs at `outputs/` or an explicitly indexed external location. Keep user task projects outside the reusable skill. Inspect existing policies/stores/queues before initialization; never create a second authoritative task queue.

No overwrite on initialization, including an existing empty destination. No symlink destination or traversal. Use a lowercase hyphenated project ID. All local index locations are project-relative POSIX file paths resolved inside the project; refuse absolute paths, `..`, symlinks escaping the root, missing files and credential-like paths (`.env`, credentials, private keys). External locations use explicit `https://`, `drive://`, `notion://`, `page://` or `s3://` references without credentials. The helper also rejects query strings and fragments; use a clean reference instead of a signed URL. Audit does not fetch them; inspect current access/version independently. Never put credentials in URLs.

## agent.json

Required top-level fields match the template: `schema_version` = 1, `project_id`, `status` (`draft`, `ready`, `blocked`), `instructions`, `playbook`, `toolbox`, `execution`, `bounds`, `capabilities`, `authority`, `retention`. The three artifact paths are local project-relative paths.

Execution `mode` is null until established, then `manual`, `one_time`, `recurring` or `event`. Always settle it; task recurrence alone is not authorization to schedule. `trigger`, `timezone`, `dependencies`, `ordering`, `overlap_policy`, `retry_policy`, `stop_conditions`, `notification` and `registration` remain explicit. For automation fill them with the user/host's actual values; timezone may be unnecessary for a purely event-based trigger if explicitly documented. Registration has `provider`, `id`, `status`, `verified_at`, `evidence`; default `unregistered`. Registered status needs current provider readback and receipt. Nulls mean unknown, not registered or completed.

`bounds`: `max_attempts` counts the initial attempt and repairs (integer ≥1); `max_minutes` is a positive finite shared effort budget; `max_depth`, `max_concurrency`, `max_workers` are nonnegative integers, with any zero disabling delegation; `max_cost_usd` is null when unmeasured or a finite nonnegative explicit cap. Zero cost is valid, never a reason to substitute a paid default. A cap of zero disallows paid execution; null does not authorize paid services. Parent and children share limits. Attempts stop earlier on repeated identical failure or inability to verify. Defaults are proposals to adapt to the task.

`capabilities` contains required/optional/observed/missing arrays; observations name actual tool and verification evidence. Missing required or undeclared capabilities block readiness; explicitly optional absence warns. Promote a capability to required when the requested mode needs it, such as a scheduler for live automation. `authority` has source/allowed/escalate/external_actions; it is a record, not restored permission. `retention.temporary_dirs` lists only disposable directories (default scratch and logs), with `temporary_days` (nonnegative integer) and a durable retention description. Expiry does not authorize deletion by the helper. Do not hide durable output under temporary exclusions. The helper rejects exclusions at or below outputs/, runs/ and toolbox/; misplaced durable data still requires independent inspection.

## toolbox/index.json

`schema_version`, `project_id`, `resources`. Each resource has:

- `id`: unique lowercase hyphenated identifier; `purpose`; `kind` (e.g. template, script, output, review, evidence, reference, playbook, configuration, instructions, index).
- `location`: unique local file path or explicit external URI; `version`: actual version/hash/provider revision, not a guessed version.
- `input_contract`, `output_contract`: nonempty text, or explicit "not applicable" with reason for passive documents.
- `dependencies`: resource ID array; all IDs must exist; no self dependency or dependency cycles.
- `status`: draft / validated / retired. `validation`: method and evidence location array; validated requires nonempty method and evidence. Evidence must exist locally or be an explicit external URI. The model independently inspects whether evidence supports the claim.
- Optional `validation.bindings` pins local source/evidence files whose byte identity matters. Each item has `role` (`source` or `evidence`), project-relative `location`, and a 64-character hexadecimal `sha256`. Evidence bindings must also appear in that resource's `validation.evidence` list. The audit streams and hashes only these explicitly listed local files, failing when current bytes differ. Omitting `bindings` preserves version-1 projects. A matching hash proves only that bytes match the recorded pin; it does not prove the pin is authoritative/current or that an outcome is correct. External references are not fetched or freshness-checked and still need current provider-version/readback and independent outcome checks.
- `used_by`: nonempty stable step/check ID array found in PLAYBOOK.md (e.g. step-01/check-01).
- `replaces`: prior resource ID or null; retain the prior entry and version. `reuse_decision`: searched matches and why reused/adapted/new/replaced.

Search by purpose, kind, input/output and location. Inspect the actual best matches, not just names. Reusable templates and individual outputs get distinct IDs. Index all durable files or references, including evidence, run records and outputs. Ignore only Git internals, checkpoint/private interview state, Python caches, and configured disposable directories; this is an inventory rule, not a secret scanner. Credentials are excluded, not indexed.

## Run/review record

Use `templates/run-review.json` without changing the meaning of fields. `status`: planned/running/passed/partial/failed/blocked/uncertain. `run_key` binds workflow, input version and trigger occurrence. Consult the authoritative host queue/lease before processing; JSON is no concurrent lock or deduplication service.

Before execution preserve `versions.acceptance_snapshot`: the frozen check table/file and version/hash. `checks` contains ID/expected/method/status/evidence/observed for each applicable criterion; status is not_run/pass/fail/blocked/unavailable/not_applicable. Explain not_applicable in observed, and use it only for a criterion the independent reviewer marked optional. Required unavailable checks forbid passed. `attempts` records number, action, elapsed effort and result; `repairs` records failure/cause/correction/playbook-or-toolbox version/affected checks/regressions and results. Index all durable record/evidence files. Independent outcome evidence can disprove procedural compliance.

`delegations` records each child contract (objective, input/output, tools, authority, allowed files, owner, shared budget/depth/checks) and reviewed return. `side_effects` records operation/run key/provider ID/status/evidence/reconciliation. Unknown completion remains uncertain and blocks retry. `usage` null stays unknown. Record exact automation readback separately from requested configuration. Stop with a verified next action when full completion cannot be established.

## Helper interface

From any directory, use the absolute helper path:

```
python3 /path/to/agent-forge/scripts/forge.py init /path/to/new-project --project-id report-agent
python3 /path/to/agent-forge/scripts/forge.py find /path/to/project --query report
python3 /path/to/agent-forge/scripts/forge.py audit /path/to/project
python3 /path/to/agent-forge/scripts/forge.py audit /path/to/project --ready
```

`init` writes the four seeded durable files using bundled templates, substitutes PROJECT_ID and leaves a draft with mode/authority unset. It creates no run, executes no task and starts no job. `find` returns JSON matching entries without modifying them. `audit` returns JSON `{ok, errors, warnings}` and nonzero on structural errors. Fresh draft structural audit passes but warns about unreadiness; `--ready` must fail for unset mode/authority, missing capabilities, placeholder playbook, nonvalidated required seed resources, or missing outcome checks/evidence. It must not claim task acceptance even when passing. There is no launch, register, credential, deletion or arbitrary command-execution function.
