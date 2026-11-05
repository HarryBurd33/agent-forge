# Project contracts, version 1

These are original local artifact contracts, not a scheduler, queue database, sandbox or autonomous runtime. Python helpers are optional; another host may edit equivalent files directly. A helper audit checks explicit structural rules, never arbitrary task quality, authorization or all secrets.

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

Before execution preserve `versions.acceptance_snapshot`: the frozen check table/file and version/hash. `checks` contains ID/expected/method/status/evidence/observed for each applicable criterion; status is not_run/pass/fail/unavailable/not_applicable. Explain not_applicable. Required unavailable checks forbid passed. `attempts` records number, action, elapsed effort and result; `repairs` records failure/cause/correction/playbook-or-toolbox version/affected checks/regressions and results. Index all durable record/evidence files. Independent outcome evidence can disprove procedural compliance.

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
