# What is verified

The repository's claims are limited to the mechanisms it includes. Agent Forge is an instruction skill with templates and a deterministic local helper. Business task execution uses the host's model/tools. Schedulers, connectors, persistent runtimes and concurrent-process fencing are conditional host capabilities.

## Reproduce the automated checks

Run these from a clean clone with Python 3.9+:

```sh
python3 scripts/verify_release.py .
python3 -m unittest discover -s agent-forge/tests -v
python3 -m unittest discover -s tests -v
```

The 25 helper tests cover draft creation, existing-work preservation, index search, paths/evidence/inventory, zero limits, malformed data, dependencies, automation receipt fields, readiness markers, opt-in source/evidence freshness bindings and independently pinned run-record conformance (including explained optional N/A). The workflow test uses a concrete existing report template and actual local file/check operations: 41 fails against source42; repair42, save/read back a playbook correction, rerun original acceptance, then a repeated request with 0+5 produces5 while preserving the template and frozen criteria. Final durable inventory is audited. This is deterministic integration evidence; no LLM is secretly called by tests.

The release verifier checks the MIT license at both root and skill level, skill metadata/display name, local references, JSON/Python syntax, package hashes and the exported file inventory. It does not certify arbitrary secret absence or domain correctness. Manifests must be updated deliberately when source changes. A stale manifest is a failed release check, rather than evidence that changed source is still validated.

[CI](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml) runs these checks on Python 3.9, 3.12 and 3.14 using pinned official checkout/setup-python action commits. Inspect the actual run conclusion for a particular commit; workflow configuration alone is not a passing result.

## Model evidence and limits

The [authoring validation report](agent-forge/validation/REPORT.md) preserves eight baseline/candidate cases, their context/comparison limitations, initial partial coverage and a supplemental actual model/tool repair cycle. This historical record predates global installation/publication. Raw private model/interview records and task projects are excluded from the repository; sanitized results and hashes are included. Examples in the reference guide are labeled illustrations.

The 0.3.0 comparison uses installed 0.2.0 as baseline and actual generated local solutions. The demonstrated gain is required-renderer repair; both arms already handled correct totals, missing input/zero, observation-dependent routing, uncertain sends and absent schedulers. The [current report](agent-forge/validation/REPORT.md) states the evidence differences, timing limitations, held-out scope and post-run conformance repair. Raw private runs remain excluded.

Native discovery is device-specific and should be verified after installation. The helper's readiness audit cannot establish whether a host has a working scheduler, whether a provider actually sent a message, or whether a prior task's output remains correct after input changes. Those require current authorization and task-specific external evidence. Unsupported capabilities must be reported, not invented.

No test establishes unlimited autonomy, a guaranteed outcome on every task, or persistent background execution from a skill file. Deterministic tests alone cannot establish registration or delivery. The separate 0.3.1 native pilot observed registration, two later receiving turns with correct local outputs, and confirmed retirement. The README capability table and skill instructions preserve those boundaries.
## 0.3.1 additional checks and observed scope

The new `tests/test_reuse_workflow.py` executes actual helper/renderer/checker subprocesses against a customized existing project, observes missing evidence then unindexed output, revalidates honestly and preserves historical files. The normal test passes; `FORGE_REUSE_CORRUPT_OUTPUT=1` intentionally fails. The model comparison separately catches a stale saved checker path and verifies a changed-input followup through the candidate's saved invocation. Fresh native CLI, staged interview, real child roles and local simulated reconciliation are recorded in the dated validation report. Automation delivery and final installed invocation must be read from their specific release evidence; no blanket scheduler/event guarantee is made.

## Installed 0.3.1 invocation — 2026-11-08

After a guarded upgrade with a verified 0.3.0 rollback copy, all 21 installed skill files matched the accepted source. A fresh Codex CLI 0.166.0 invocation discovered and loaded installed Agent Forge 0.3.1, generated a small manual adapter and actually checked `[4,0,9]` → exactly `Total: 13`, missing `rows` → exit2 with empty stdout, and `[0]` → exactly `Total: 0`. An independent parent reran those checks and verified the loaded skill hash. Total observed CLI duration was 75.146 seconds; reported usage was 148138 input tokens, 105856 cached input tokens and 2662 output tokens. Token categories are provider-reported; account allowance was not converted to task cost. No paid API fallback was used. Raw task traces and local installation paths are private.

## 0.3.2 recovery evidence

The dated skill report separates the actual generated-workflow comparison from six deterministic process regressions. The latter use separate runner/provider processes and provider-owned effect/call records. A legacy-guard control must fail; no model is secretly called by the test suite. Run the commands in tests/RECOVERY.md from the tests directory. The current release installation/invocation and remoteCI are checked separately.

Installed0.3.2 was then discovered and loaded by a fresh Codex CLI0.166.0 invocation using the existing ChatGPT sign-in and no paidAPI fallback. Actual and independently rerun checks produced13, rejected missing rows with exit2, and preserved0. All21installed skill hashes matched accepted source. CLI duration59.298s; provider-reported168352input,145024cached input and2023output tokens. No account allowance was converted to task cost. Raw native traces remain private.

## 0.3.3 concurrent task qualification

The 0.3.2 builder passed a new actual native-child case; 0.3.3 changes coverage and documentation, not operating behavior. Two workers inspected different source formats under one parent-owned budget, with an actual missing-field stop, overlapping task/tool lifetimes, pending-handle reconciliation and independently recomputed integration. The saved procedure then consumed changed inputs and fresh outputs under the same five-dispatch limit. See [the dated validation report](agent-forge/validation/REPORT.md) and [verified workflow](agent-forge/references/verified-workflows.md).

Run `python3 -m unittest discover -s tests -p 'test_parallel_workflow.py' -v` for the portable local protocol tests. Their host observations are explicitly synthetic; they do not replay model execution. The private native run established task/tool overlap with a bounded coordination barrier, not simultaneous inference or faster execution. See `tests/PARALLEL.md` for the negative control and remaining limits.

## 0.4.0 runtime applications and code review — 2026-11-12

Agent Forge now has an explicit read-only code-review path and a version-matched runtime-application path. New agent applications default to evaluating Eve against their requirements; direct tasks and established stacks remain supported. The optional Git helper resolves targets and emits complete patches; it does not detect defects.

Actual comparable Codex/Sol Medium runs used the previous 0.3.3 and candidate 0.4.0 instructions with the same synthetic requests. Both returned 13 for [4,0,9], preserved an existing Python workflow, found both seeded regressions, excluded unchanged/style-only issues, and left full repository bytes unchanged. The baseline proposed a custom Django agent runtime; the candidate selected Eve with pinned, installed documentation. The candidate used the upstream-aware merge base and produced prioritized findings. Review elapsed time was 46.761s baseline and 43.032s candidate; routing was 50.060s and 43.493s. These single runs do not establish a speed or cost advantage. A held-out installed-version case correctly read rc.9's scheduling guidance in 32.461s.

The [original synthetic runtime fixture](examples/eve-local/README.md) exercised actual Eve 1.0.0-rc.9 mechanics with a deterministic mock model and no paid inference: typed tool totals13/0, missing-input rejection before tool execution, safe ACTION_RESULT_FAILED handling, an on-demand skill load, and nine strict eval gates. A parent-owned independent check observed authenticated local events, HTTP401/400 rejection, remembered-key duplicate and changed-payload suppression, actual tool totals13 then7 in the same session across distinct stopped/restarted processes, preserved history, and a saved SDK cursor without replay. Both processes exited and their listeners closed. A separate one-shot development-schedule dispatch produced tool total3. This is not cron-cadence or external-provider verification.

The scaffold initially resolved rc.10 through a caret despite a pinned rc.9 initializer. The fixture and guidance now verify manifest, lockfile and installed version together. A fresh registry install of the exact lockfile and typecheck succeeded. Two parent evaluator implementation errors (a parameter-name collision and assuming scalar event positions) were preserved and corrected against the actual interface; criteria were unchanged, and the complete corrected run passed.

Seven new executable Git-target regressions cover upstream ahead/divergence/fallback, staged/unstaged/untracked/unborn and clean states, root/merge/custom targets, missing shallow objects, and suppression of external diff/textconv/filter effects. Full repository hashes must remain unchanged. Together with the38 prior checks,45 Python tests pass. CI exercises those Python checks and static release contracts; the optional Node/Eve fixture was executed locally and is reproduced through its playbook. Raw model records, local stores and private runs are not distributed.

Remaining gates for a particular deployment: live OAuth/MCP/provider delivery, authenticated browser rendering and cancellation, managed sandbox isolation, multi-replica fencing, actual runtime child isolation/budgets, crash recovery during an Eve effect, migrations, and sustained scheduler availability. The runtime guide maps every requested capability to versioned docs and concrete verification; documentation coverage does not turn those deployment gates into verified guarantees.

Fresh installed invocation then discovered and loaded Agent Forge0.4.0 without a supplied skill path. It reproduced both seeded regressions with priorities and the correct upstream merge base, returned `No findings.` for the clean comparison, and preserved all114 repository-file hashes. Duration43.713s; reported322333 input,274048 cached input and1236 output tokens. All25 installed skill files matched accepted source. No task-dollar estimate was inferred.
