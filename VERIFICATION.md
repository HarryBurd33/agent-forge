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
