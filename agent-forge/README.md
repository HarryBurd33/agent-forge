# Agent Forge

Build a task agent from a working method: interview selectively, capture a playbook, reuse an indexed toolbox, configure execution and verify results. The reusable skill is `agent-forge`; its Codex display name is **Agent Forge**. Version 0.3.1.

Choose a direct reusable prompt/tool call, a fixed workflow, or an observation-driven agent according to the task evidence. A direct solution can stay small; known branches do not require autonomous planning. Approach is separate from manual or automated execution.

This folder is the reviewable skill package. Task-specific projects, private interview notes, checkpoints and generated business outputs belong elsewhere.

## Use without installation

In a capable agent host, ask:

> Read `/absolute/path/to/agent-forge/SKILL.md` and use Agent Forge to turn my weekly report method into an agent. Use my existing template; prepare manual invocation first.

After an authorized installation in the host's skill directory, use:

> Use $agent-forge to build an agent for my document review process.

To install from the public source, ask Codex: “Use $skill-installer to install agent-forge from HarryBurd33/agent-forge, path agent-forge, as a user-level skill.” It will be available on the next turn; restart Codex if it does not appear. Installation applies to the current device/account. The [public repository](https://github.com/HarryBurd33/agent-forge) contains the root MIT license, CI and reproducible release/workflow tests.

For an existing project:

> Use $agent-forge to repair this agent's failed quality check. Inspect its PLAYBOOK.md and toolbox first; preserve its acceptance criteria.

An ordinary request such as “summarize this report” does not activate the builder. Mentioning agents in source text is not a trigger.

## Setup and helper

The core needs artifact read/write, search and task-outcome validation. No Python is needed to follow the instructions or edit the templates manually. The optional helper needs Python 3.9+ and its adjacent `templates/` folder; no pip packages, API key, daemon or third-party runtime is required.

```
python3 /absolute/path/to/agent-forge/scripts/forge.py init /absolute/path/to/new-report-agent --project-id report-agent
python3 /absolute/path/to/agent-forge/scripts/forge.py find /absolute/path/to/report-agent --query report
python3 /absolute/path/to/agent-forge/scripts/forge.py audit /absolute/path/to/report-agent
python3 /absolute/path/to/agent-forge/scripts/forge.py audit /absolute/path/to/report-agent --ready
```

The destination's parent must exist. Initialization refuses an existing destination and creates a draft; mode and authority remain unset. Fill the playbook and configuration, teach back and dry-run the method, define fixed outcome checks and inspect evidence before treating the agent as ready. Optionally pin local source/evidence bytes with `validation.bindings` entries; audit checks those hashes but cannot prove the pins are authoritative/current. Structural audit can pass while an outcome is wrong. `--ready` checks markers and evidence references, not the truth of arbitrary domain claims.

Workflow/agent scaffolds contain AGENT.md, PLAYBOOK.md, agent.json and toolbox/index.json. Copy the run/review template into the project's run directory when planning execution and index it. See [contracts](references/contracts.md) for fields, path rules and statuses. Index every durable output separately from reusable templates. Preserve credentials outside the project and private task data outside this skill distribution.

For run-record conformance against a separately owned frozen acceptance snapshot:

```sh
python3 scripts/forge.py audit-run /absolute/path/to/report-agent --record runs/01/review.json --criteria /reviewer/criteria.json --criteria-sha256 EXPECTED_SHA256
```

See [the exact acceptance-file contract](references/contracts.md). This checks required check IDs, matching criteria, complete evidence fields and consistent terminal status. It does not establish that evidence is true or task outputs are correct. Keep evaluator ownership separate and inspect actual outputs. [Engineering guidance](references/engineering.md) covers tool-interface inspection, observation-driven recovery and redacted diagnostic events.

## Launch and automation

For a prepared task project, ask a host to read its AGENT.md and run the authorized playbook within its configured limits. [Codex setup](references/codex.md) gives the checked CLI syntax and capability limitations. A prepared project is not a launched agent. No job is active merely because agent.json contains a schedule.

The builder always establishes manual, one-time, recurring or event execution intent. Real automation needs an authorized supported scheduler/queue, actual registration/readback and verified dependencies, overlap, retries and notification behavior. Inspect existing jobs first. Without that capability deliver unregistered configuration. Unknown external outcomes block duplicate actions until reconciled. No scheduler, cross-process lease, persistent background agent or provider integration is bundled.

For later installation, copy the complete `agent-forge/` directory into a host-approved skill location only when authorized. For Codex that may be a repository's `.agents/skills/`; preserve any existing customized copy. No installation is performed by the helper. For export, ZIP this complete directory with relative paths, excluding caches and all task projects/private state. No publication is implied.

## Checks and limits

```
python3 -m unittest discover -s /absolute/path/to/agent-forge/tests -v
```

[Validation evidence](validation/REPORT.md) separates structural checks, executed utilities, actual model/tool exercises, illustrations and live checks not run. [Examples](references/examples.md) are illustrations. [Sources](SOURCES.md) records inspected foundations and rights. The skill is original MIT source; no dependency on Skill Forge or task-checkpoint is required.

Default bounds are proposals: three total attempts, 30 minutes shared effort, depth 1, concurrency 2, two workers total. Adapt to the task and host before execution. Explicit zero disables delegation; unknown costs stay unknown. Parent review, repair and child work all consume the same limits. Stop with a useful partial/failure report when evidence, authority or resources are insufficient.
## Verified reuse and host boundaries

The [reuse recipe](references/verified-workflows.md) covers missing validation evidence, unindexed historical output and consistent per-run bindings. A saved-procedure changed-input run now accompanies the actual output check. See the dated validation report for native CLI, staged interview, actual child work and local reconciliation evidence. These are bounded observations, not universal reliability or process-enforcement guarantees.
