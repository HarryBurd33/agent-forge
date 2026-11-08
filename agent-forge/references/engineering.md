# Engineering choices that can be checked

Use the least elaborate solution that meets the observed task. These are design choices, not a required framework, fixed sequence of model calls, or permanent process.

| Approach | Evidence it fits | Deliverable and check |
|---|---|---|
| `direct` | All necessary input is supplied; one transformation/answer or known tool call suffices | Reusable prompt/tool contract, representative output and missing-input check. No project scaffold unless needed or requested. |
| `fixed_workflow` | The ordered stages and allowed branches are known before execution | A playbook or small program with explicit gates; check intermediate and final outputs. |
| `observation_driven` | A result determines which next action/tool/identifier is appropriate | Bounded action/observation loop, completion and stop rules, independently checked outcome. |

Do not infer an agent is needed because the task recurs or uses tools. State the reason for complexity in terms of actual ambiguity, variability or failed simpler behavior. Unknown benefit stays unknown. Revisit the choice when observations change; preserve the prior decision/evidence.

A fixed workflow can dispatch known error codes and follow returned handles. Those observations alone do not justify autonomous planning. Use an observation-driven agent when useful actions or a plan must be selected or revised beyond a complete predeclared branch table; test that distinction instead of scoring the label.

Use **routing** only when distinguishable input classes need different paths; test uncertain or overlapping categories. Use **stages** when an intermediate result has an independent gate. Use **parallel work** only for independent useful subtasks, with host support, nonoverlapping ownership and a shared budget that permits children. Zero depth, concurrency or workers means no delegation. Use **critique/repair** when a concrete criterion can diagnose a fixable failure; cap iterations and retain the unchanged evaluator. A critic's preference is not an independent correctness oracle. These patterns may combine, but each needs a task-specific reason.

## Inspect the tool interface

For each callable tool, record or link an actual inspected contract:

- Purpose and exclusions: what changes, what is read, and which overlapping tool to use instead.
- Required/optional inputs, types, enum values, units, absent versus empty/zero, valid identifiers and how to obtain them.
- Output fields and meanings, version/freshness, success versus partial/unknown results.
- Error codes, retryable conditions, maximum attempts, idempotency/readback and uncertain-outcome recovery.
- Side-effect class (`read_only`, `local_write`, `external_write`), authority needed and rollback limits.
- One valid example and the likely mistakes tested. Keep examples synthetic and credentials outside artifacts.

Examples: a search tool returns candidate IDs while a fetch tool accepts one exact ID; a renderer writes an output while a checker compares it with the source. Do not use a search query as an ID or treat the renderer's success flag as a passed outcome check. Prefer clarifying the interface and reducing ambiguity before adding another prompt or agent. Report a tool defect separately from a bad model choice.

## Run from observations

1. Validate required inputs and current scope. Valid zero is not missing. Freeze outcome criteria and source/tool versions before candidate execution.
2. Read existing run ownership, shared budget and uncertain effects. Reconcile before repeating an external action.
3. Perform the allowed step. Record the tool name, sanitized input/reference and actual result/error with an evidence ID.
4. Select the next action from that result: advance, route, retry a specifically retryable safe error within bounds, repair a failed check, stop, or escalate. Save a concise decision summary tied to the evidence.
5. Independently check completion. On a reusable failure, save and read back the playbook/tool correction before rerunning the unchanged affected checks and regressions.

Missing required input blocks dependent work. A deterministic validation error requires correction, not repeated identical calls. A transient read error can permit a bounded retry. An unknown external write outcome requires reconciliation; a timeout is not proof of failure. Missing scheduler support permits unregistered configuration only. A successful registration proves registration, and observed delivery proves only that particular execution; neither establishes indefinite recurrence or process fencing.

## Evidence and evaluation

Use `run-review.json` for summaries and references, not unrestricted transcripts. Capture input/output hashes or provider revisions, tool and solution versions, actual calls/results, error categories, attempt/resource use, stop reason and independent outcome evidence. Do not retain hidden reasoning, credentials or unrelated personal data. Sanitize before writing; a secret excluded from the summary must not survive in a second raw log. Hashes establish byte identity, not source authority or correctness.

The reviewer freezes expected results, evaluator code and versions outside the candidate's permitted writes. Compare actual executions under the same inputs, tool fixtures and model/effort where supported. Report mismatches, unknown usage, latency method and sample size. Include a held-out changed observation to expose scripts that replay a memorized tool sequence. Check final correctness, tool choice, stopping, saved learning and regressions. A structural audit, authored example or narrated successful run is not behavioral evidence.

Keep a candidate isolated when required evidence is missing or no intended benefit is observed. Do not rewrite the acceptance rule to admit it. The helper does not enforce access isolation, scheduler guarantees, runtime budgets or cross-process ownership; use supported host mechanisms and disclose what they actually enforce.
