# Agent Forge

[![CI](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/HarryBurd33/agent-forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A reusable Codex skill that turns a working method into a task agent: focused interview → playbook → reusable toolbox → bounded run → check → fix → saved playbook update → rerun.

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

## What a project contains

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
| Local scaffolding and audit | Python standard-library CLI, unit tests, manifest/link verification | Explicit SHA-256 pins catch local source/evidence drift; unpinned and external sources still need runner checks, and hashes do not prove correctness |
| Check/fix/update/rerun | Actual model repair example and reproducible local workflow test | Bounded attempts; no guarantee every task can be repaired |
| Delegation | Child contracts, shared limits and parent review instructions | Needs host orchestration; instructions alone do not fence tools or concurrent processes |
| Scheduling/events/queues | Configuration and registration/readback procedure | Requires supported authorized host integration; no scheduler bundled |
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

The new project's parent directory must exist. Initialization refuses existing destinations and leaves a draft. The final `--ready` command is expected to fail until readiness fields and evidence are supplied. The helper does not execute the business task or register jobs.

## Verify a checkout

```sh
python3 scripts/verify_release.py .
python3 -m unittest discover -s agent-forge/tests -v
python3 -m unittest discover -s tests -v
```

GitHub CI runs these commands on Python 3.9, 3.12 and 3.14. The workflow test exercises an existing template, a deliberately wrong total, frozen acceptance, repair, a saved playbook correction, a zero-value regression, a repeated request and a final inventory audit. It is a deterministic fixture rather than an LLM benchmark. The release verifier checks metadata, links, JSON/Python syntax, MIT licenses and file manifests.

The published repository is exported from an explicit file allowlist. It contains no private build history, raw interview/model logs, task checkpoint database or generated business outputs. [Sources and reuse decisions](agent-forge/SOURCES.md) record the inspected foundations. Original code and instructions are under the [MIT License](LICENSE).
