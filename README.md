# Agent Forge

[![CI](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A reusable Codex skill that turns a working method into a task agent: focused interview → playbook → reusable toolbox → bounded run → check → fix → saved playbook update → rerun.

Version 0.4.0 selects a direct reusable prompt/tool call, a fixed workflow, or an observation-driven agent from task evidence. Known branch tables can remain fixed workflows. Full projects are created when useful.

Agent Forge creates and maintains concrete agent projects. It uses the host's tools and current authorization for execution. Its Python helper scaffolds, searches and audits local artifacts. Scheduling and persistent execution require a supported host integration.

## Install for all your Codex chats

In Codex, ask:

```text
Use $skill-installer to install agent-forge from the
HarryBurd33/agent-forge GitHub repository, path agent-forge.
Install it as a user-level skill, available across my local projects.
```

It will be available on the next turn. If it does not appear in the skill selector, restart Codex. Installation is local to that device/account; other devices need their own installation. This is the standard [Codex skill installation and invocation](https://learn.chatgpt.com/docs/build-skills) workflow.

To use without installation, clone this repository and ask a capable host to read the full `agent-forge/SKILL.md`. For manual installation, copy the complete `agent-forge/` folder into an approved user skill directory, preserving an existing customized copy. See the [skill setup guide](agent-forge/README.md).

## Use it

```text
Use $agent-forge to build an agent for my weekly operations report.
I have an existing template and source spreadsheet. Interview me only
about material gaps, reuse my resources, and start with manual execution.
Save the agent project in ./report-agent.
```

```text
Use $agent-forge to turn my document review process into an agent.
Ask me about judgment calls and show me a representative dry run
before treating it as ready.
```

```text
Use $agent-forge to repair the agent in ./report-agent.
Read its PLAYBOOK.md and toolbox first. Preserve its acceptance criteria,
fix the failed output, save the validated lesson, and rerun affected checks.
```

For automation, explicitly request the desired trigger, timezone, overlap/retry policy and notifications. Agent Forge inspects existing jobs and reports a registration only after actual host readback. Without scheduler access it prepares unregistered configuration. An ordinary request to summarize a document does not start an agent-building interview.

## What a workflow or agent project contains

| Artifact | Purpose |
|---|---|
| `AGENT.md` | Bounded runner instructions and review cycle |
| `PLAYBOOK.md` | Task method, decisions, examples, permissions, checks and lessons |
| `agent.json` | Execution intent, observed capabilities, scope and finite limits |
| `toolbox/index.json` | Searchable inventory of reusable resources and individual durable outputs |
| Run/review records | Frozen criteria, actual evidence, failures, repairs and next action |

Projects and private interview records belong outside the reusable skill. Credentials belong in the host's credential store.

## Capabilities and evidence

| Capability | Implementation and evidence | Boundary |
|---|---|---|
| Task interview and playbook/package creation | Skill instructions, templates and actual local model examples | Domain judgments still need suitable examples and checks |
| Resource search and reuse | `find`, toolbox contract, repeated-template workflow test | The model must inspect whether a match fits |
| Run-record conformance | `audit-run` compares complete checks with separately pinned criteria; 25 helper tests cover current helper behavior | Conformance does not prove evidence truth or domain correctness |
| Local scaffolding and audit | Python standard-library CLI, unit tests, manifest/link verification | Structural checks cannot prove arbitrary domain correctness |
| Check/fix/update/rerun | Actual model repair example and reproducible local workflow test | Bounded attempts; no guarantee every task can be repaired |
| Delegation | Child contracts plus two actual child roles, one bounded retry and reviewed integration | Needs host orchestration; instructions alone do not fence tools or concurrent processes |
| Scheduling/events/queues | Configuration plus two observed native timer deliveries and cleanup; event integration unavailable on the tested host | Requires supported authorized host integration; no scheduler bundled |
| Persistent execution and external actions | Host-provided runtime and connectors | No daemon, cross-process lock or external service included |

[Validation evidence](agent-forge/validation/REPORT.md) distinguishes actual model/tool runs, deterministic tests, authored examples and unexecuted live integrations. Synthetic tests demonstrate specific behavior; they do not establish universal reliability.

## Helper CLI

Python 3.9+ is needed only for the optional helper and tests. No pip packages or model API key are needed for these commands. From a clone:

```sh
python3 agent-forge/scripts/forge.py init ../new-report-agent --project-id report-agent
python3 agent-forge/scripts/forge.py find ../new-report-agent --query playbook
python3 agent-forge/scripts/forge.py audit ../new-report-agent
python3 agent-forge/scripts/forge.py audit ../new-report-agent --ready
```

The new project's parent directory must exist. Initialization refuses existing destinations and leaves a draft. The final `--ready` command is expected to fail until readiness fields and evidence are supplied. The helper does not execute the business task or register jobs. For explicit run-record checking, use `audit-run PROJECT --record runs/01/review.json --criteria /reviewer/criteria.json --criteria-sha256 EXPECTED_SHA256`; see the [criteria contract](agent-forge/references/contracts.md).

## Verify a checkout

```sh
python3 scripts/verify_release.py .
python3 -m unittest discover -s agent-forge/tests -v
python3 -m unittest discover -s tests -v
```

GitHub CI runs these commands on Python 3.9, 3.12 and 3.14. The workflow test exercises an existing template, a deliberately wrong total, frozen acceptance, repair, a saved playbook correction, a zero-value regression, a repeated request and a final inventory audit. It is a deterministic fixture rather than an LLM benchmark. The release verifier checks metadata, links, JSON/Python syntax, MIT licenses and file manifests.

The 0.3.0 actual generated-solution comparison demonstrated a narrow improvement: repair used the task-required renderer after a failed check, where the 0.2.0 baseline directly rewrote its output. Both produced correct totals. Other synthetic behaviors and the unseen-observation regression passed in both arms; no broad reliability or efficiency gain is claimed.

The published repository is exported from an explicit file allowlist. It contains no private build history, raw interview/model logs, task checkpoint database or generated business outputs. [Sources and reuse decisions](agent-forge/SOURCES.md) record the inspected foundations. Original code and instructions are under the [MIT License](LICENSE).
## 0.3.1 verified reuse update

Reusing a project now includes checking every active saved source/output/evidence reference and executing an authorized bounded follow-up from the saved procedure. The new comparison caught an old checker path despite a correct report, then verified the next changed-input run against the new output. Additional actual interviews, child tasks, local recovery paths and fresh CLI invocation strengthen evidence for existing behavior. Read the validation report for precise automation status and host limits; this is not an autonomous runtime or bundled scheduler.

## 0.3.2 pending recovery

An unresolved lookup ends the current invocation while preserving a later authorized readback path. The observed baseline runner saved an unknown state that its own resume guard rejected; a workflow generated from the revised instructions resumed that same intent after later provider resolution. Identity conflicts stop, and repeated readback consumes the original budget. [Recovery regression](tests/RECOVERY.md) documents the reproducible local process test.

## 0.3.3 concurrent delegation coverage

This release adds actual concurrent task-child qualification and portable local protocol regressions. The 0.3.2 builder passed the new case, so operating instructions and helper behavior are unchanged. Two native children audited different source formats; the parent recomputed their results, retained a pending handle and enforced the shared dispatch bound. A saved-procedure follow-up changed the selected source while preserving prior artifacts. See the [validation report](agent-forge/validation/REPORT.md) for evidence and limits. The repository tests replay local subprocesses with synthetic host observations; they do not launch model agents or prove host-wide enforcement.

## 0.4.0 applications and code review

Build concrete runtime applications through [version-matched Eve guidance](agent-forge/references/runtime-apps.md), or perform a [read-only defect review](agent-forge/references/code-review.md) of uncommitted changes, a base branch, a commit or a custom scope. Agent Forge remains dependency-free; Eve is optional for generated applications. Try the [local synthetic fixture](examples/eve-local/README.md) for tools, skills, authenticated events, session restart, SDK streams and evals. Hosted integrations remain conditional on actual setup and verification. See [verification](VERIFICATION.md) for measured results and limits.
