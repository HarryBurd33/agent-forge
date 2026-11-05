# What is verified

The repository's claims are limited to the mechanisms it includes. Agent Forge is an instruction skill with templates and a deterministic local helper. Business task execution uses the host's model/tools. Schedulers, connectors, persistent runtimes and concurrent-process fencing are conditional host capabilities.

## Reproduce the automated checks

Run these from a clean clone with Python 3.9+:

```sh
python3 scripts/verify_release.py .
python3 -m unittest discover -s agent-forge/tests -v
python3 -m unittest discover -s tests -v
```

The 17 helper tests cover draft creation, existing-work preservation, index search, paths/evidence/inventory, zero limits, malformed data, dependencies, automation receipt fields, readiness markers, legacy indexes without freshness bindings, unchanged SHA-256 pins, and changed source/evidence rejection. The workflow test uses a concrete existing report template and actual local file/check operations: 41 fails against source42; repair42, save/read back a playbook correction, rerun original acceptance, then a repeated request with 0+5 produces5 while preserving the template and frozen criteria. Final durable inventory is audited. This is deterministic integration evidence; no LLM is secretly called by tests.

The release verifier checks the MIT license at both root and skill level, skill metadata/display name, local references, JSON/Python syntax, package hashes and the exported file inventory. It does not certify arbitrary secret absence or domain correctness. Manifests must be updated deliberately when source changes. A stale manifest is a failed release check, rather than evidence that changed source is still validated.

[CI](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml) runs these checks on pushes to `main` and `codex/**`, pull requests, and manual dispatch, using Python 3.9, 3.12 and 3.14 with pinned official checkout/setup-python action commits. Inspect the actual run conclusion for a particular commit; workflow configuration alone is not a passing result.

## Model evidence and limits

The [authoring validation report](agent-forge/validation/REPORT.md) preserves eight baseline/candidate cases, their context/comparison limitations, initial partial coverage and a supplemental actual model/tool repair cycle. This historical record predates global installation/publication. Raw private model/interview records and task projects are excluded from the repository; sanitized results and hashes are included. Examples in the reference guide are labeled illustrations.

Native discovery is device-specific and should be verified after installation. The helper hashes only explicitly bound local files. It does not infer missing bindings, fetch external references, establish that a recorded pin came from the current authoritative source, or establish whether a prior task's output remains correct after input changes. Those require current authorization, source-version/readback, and task-specific outcome checks. Unsupported capabilities must be reported, not invented.

No test establishes unlimited autonomy, a guaranteed outcome on every task, persistent background execution from a skill file, or actual registration of live automations. The README capability table and skill instructions preserve those boundaries.
