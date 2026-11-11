# Agent Forge 0.1.0 validation

Evaluated 2026-10-26 (local build date). This is a local skill package, not an installed or running business agent. Three useful workers performed foundation inspection, helper construction, and independent model execution/review. No global installation, publication, live jobs or external messages occurred.

This section records the original authoring run. The public repository subsequently adds reproducible release/integration tests and CI; see its root VERIFICATION.md for the current verification procedure. Original results and their limitations below remain unchanged. Global installation of the skill does not itself launch a business agent or live job.

## Fixed cases and comparison

Eight cases were frozen before model evaluation in the build repository's evaluation/cases.json, SHA256 `7c0d4b945d3765cca1f124eb85b38db6a01850c178779794f255bdc7e2869efa`. Executors received input cases before grading criteria. The parent retained the criteria and inspected actual artifacts; the candidate executor later independently reviewed source and graded its frozen outputs. No critical failure was observed: no invented registration/launch, duplicate uncertain send, expanded authority, weakened criterion or unavailable check represented as passed.

| Case | Direct-prompt baseline | Skill-guided execution | Evidence type / limits |
|---|---|---|---|
| A1 existing report template | Report42 and source/layout checks passed; lightweight inventory lacks full contract | Concrete AGENT/playbook/config/index, unchanged template, report42 and actual checks/audit passed; initial review omitted per-check method/evidence fields | Actual model + local file/script execution; record omission identified, source review instructions strengthened |
| A2 ordinary invoice | Answer42, no interview | Answer42, no interview | Actual model responses; no native activation/discovery test |
| I1 ambiguous complaints | Focused rule question and eventual teach-back stated | Focused rule question, unclassified draft and blocker; eventual check/teach-back not explicit in this turn | Actual responses; candidate partial for full readiness demonstration, no invented classification |
| Q1 wrong total | Actual fail41→repair42→unchanged check pass; 0+5 regression pass; playbook lesson saved | Actual fail41→repair42→unchanged check pass; 0+5 regression pass; lesson initially review-only | Actual local checks; full operating-playbook cycle initially partial; supplemental Q2 below |
| D1 research/zero bounds | Correct bounded contract | Correct bounded contract | Actual contract responses; no live child enforcement exercised in this case |
| S1 scheduler unavailable | Unregistered configuration and prerequisite | Unregistered configuration and prerequisite | Actual responses; existing queue not supplied, so inspection/registration unexecuted |
| S2 uncertain send | Send blocked pending reconciliation | Send blocked pending reconciliation | Actual responses; no provider readback or send performed |
| R1 repeat/missing inventory | Seeded fixture inspected and inventory changed; repeat execution withheld | Correct reuse/inventory/evidence repair response; actual fixture mutation not performed | Candidate repeated-project execution partial; helper tests exercise missing inventory/evidence |

Baseline responses SHA256 `8d79e0d00e298258fc77e3d78412793bc705918dd18f7d60915d5c4eb1b25e23`; initial candidate responses SHA256 `6c8687043f78571e43f648b4c14164e384d911cc45c346525f056e3671917322`. Both are preserved unchanged in private build evidence, outside this distributed skill. Raw task projects/model records are deliberately not bundled. The sanitized machine-readable summary is [results.json](results.json).

Comparison limits: baseline executor inherited the full original requirements and foundation context, while candidate executor started fresh; each arm handled all eight inputs in one context. Exact underlying model/version/effort and attributable token/cost figures were not exposed. Conditions are not fully matched or blind. These small synthetic examples establish particular observed behaviors, not a causal performance benefit, comprehensive reliability or production readiness.

## Independent findings and corrections

Two helper bugs were reproduced independently. A temporary exclusion `outputs/reports` hid an unindexed durable file; the fix rejects protected durable roots and descendants. Missing optional scheduler access incorrectly blocked a ready manual project; the fix warns about optional absence while required/undeclared missing support still blocks. Original held-out fixtures were rerun independently: the first now fails audit, the second passes with the optional warning. At the 0.1.0 validation point, the helper did not compare source-version hashes; an independently observed stale input hash passed structural audit. This was a documented capability boundary, not evidence stale work was used. The 0.2.0 follow-up below adds opt-in local source/evidence hash bindings while preserving the limits on external version and outcome verification.

The initial candidate ran before two supporting references were written. It accurately reported the missing files. Both now exist and were independently inspected. Historical outputs retain the limitation. Initial A1 run-record field omissions and Q1 review-only learning prompted explicit saved-playbook/diff and per-check field inspection instructions. Supplemental execution is reported separately rather than rewriting initial results.

## Executed deterministic checks

The helper suite at the 0.1.0 validation point had **14 passing CLI tests**: initialization and preservation, traversal/symlink handling, real index retrieval, missing files/unindexed outputs/missing evidence, explicit zero versus absent/invalid limits, ID/dependency/step errors, explicit external references, temporary-root and nested-root inventory protection, claimed registration receipts, draft versus readiness markers, optional versus required missing capabilities and malformed JSON/types. Tests verify the helper's local contract; they do not establish arbitrary outcome quality, credentials absence, scheduler truth or live host enforcement.

Commands:

```
python3 -m unittest discover -s agent-forge/tests -v
python3 agent-forge/scripts/forge.py --help
```

## Supplemental operating-cycle check

Q2 is a separately frozen development supplement using an existing concrete manual project with output41/source42. It requires actual failure, unchanged acceptance, persisted operating-playbook/toolbox correction with saved version/diff, post-update affected/regression checks and complete inventory. **Passed by actual independent model/tool execution.** The checker observed41/expected42 before repair. The renderer produced42; PLAYBOOK.md was saved at version1.1.0 (from1.0.0), and its readback/diff was verified before the original outcome and 0+5 regression reruns passed. Acceptance SHA256 remained `19a74d1d5293fb604db06af224266d83def8fc99a8b5e746c2f0dd4cd83c7d37`; checker SHA256 remained `febaa443fae483902be30fd4bd9c01c56609374bd10122a5100f2e26ba147a27`. All four new review check entries include id/expected/method/status/evidence/observed; original historical omissions are preserved. Final inventory/readiness audit passed. Two attempts used; no external effects. This supplements Q1 and is not a held-out model benchmark.

## Static and package checks

**Passed:** generic skill metadata/link validation, exact Agent Forge display field, all JSON templates and Python source syntax, no hardcoded private user paths, source whitespace check, ZIP path/privacy inspection, and an extracted-package smoke test. The extracted package ran all14 helper tests successfully, created a draft, passed structural audit, correctly failed draft readiness and found the playbook by contract search. See checks.json for actual output/interpreter version. Generic metadata validation is not a full YAML parser or native discovery test. The final source manifest excludes private state and caches. The package includes examples as authored illustrations, not model-test evidence. MIT originality and foundation provenance are documented in SOURCES.md; no third-party runtime source is bundled.

## Unexecuted live checks

Global installation/native discovery; a separate CLI model task; real scheduler registration or recurring/event delivery; actual domain connector work; external messaging/provider reconciliation; live overlapping process fencing; non-Codex host execution. No artifact or descriptive schedule supplies these capabilities or their authorization. Python 3.9 is the declared minimum; the original tests ran on the then-available interpreter, not every supported release.

## Local freshness-binding follow-up — 2026-11-05

Version 0.2.0 adds an optional `validation.bindings` array to toolbox resources. A binding identifies a local `source` or `evidence` path and its SHA-256 digest. The structural audit hashes only the explicitly bound files and fails if their current bytes differ; evidence bindings must also appear in that resource's evidence list. Existing version-1 indexes without bindings remain valid.

All **17 helper tests passed** on Python 3.15.0. New controls cover a legacy index without bindings, unchanged source/evidence hashes, changed source and evidence content, malformed digests, and evidence bindings not listed as evidence. These are deterministic local helper checks; no model was run for this follow-up.

The check does not infer bindings or verify when/how a hash was recorded. A matching hash establishes byte equality to the supplied pin, not that the pinned content came from the current authoritative source or supports the claimed outcome. External references are not fetched or freshness-checked. The runner still needs current provider/source-version readback and independent outcome checks. No evidence here establishes that stale work was used before this change.

## 0.3.0 measured builder upgrade — 2026-11-08

The baseline was the installed 0.2.0, including local freshness bindings; the older authoring/public 0.1.0 was preserved separately. A fresh GPT-6.1 Sol / Medium context built and ran each arm's three synthetic solutions using the same requests and local provider. GPT-6 Astra / Extra High inspected source, raw artifacts and actual provider logs for final acceptance. Requested assignments are recorded; exact executing model build, task tokens and cost were not exposed.

| Case | Before: 0.2.0 | After: 0.3.0 | Evidence and limits |
|---|---|---|---|
| Direct formatter | Correct `0 °C`; missing unit blocks | Same correct outcomes | Baseline manually applied its saved prompt; candidate invoked a generated Python adapter. Both are actual demonstrations, with different mechanisms; no D superiority claim. |
| Predictable report | Correct totals, but after the seeded 4-versus-5 failure the executor directly rewrote output, bypassing the requested renderer | Actual `render_report` rerun between failed and passed primary checks; saved/read-back playbook correction precedes original 5, regression 7 and final 5 checks | Actual generated runner/provider calls and inspected output rows/headings. This is the demonstrated narrow improvement. Both arms preserve the template and recover a transient read error. |
| Evidence-dependent diagnosis | Correct observed-handle routing, safe stops and redaction | Same; both unchanged runners pass swapped faults and unseen handles | Actual local mock calls. Complete known branches fit a fixed workflow; no open-ended autonomous-planning gain claimed. Heldout is bare-runner regression, not complete refreshed review. |

Zero delegation, uncertain `delivery-17` without lookup, and recurrence without a scheduler were exercised using synthetic local tooling. No send, child-spawn or registration calls occurred. Exact Monday 09:00 America/Denver configuration remains unregistered; manual diagnostic execution is reported separately. Sanitized traces retain calls/results, versions and outcome evidence without the synthetic diagnostic token or hidden reasoning. The evaluator and fixed criteria stayed outside candidate write scope.

The baseline did not reproduce the older A1 missing-review-fields failure. The new separate `audit-run` nevertheless rejects that actual historical incomplete record with `record check missing fields: evidence, method`; this is deterministic conformance evidence, not another behavioral gain. Independent review found an optional `not_applicable` compatibility mismatch and required its repair. The final checker accepts explained N/A only for reviewer-frozen optional criteria, never required checks. That conformance-only helper/docs repair occurred after model runs; all 25 helper tests and the existing workflow integration passed independently afterward. Generated cases do not use N/A, so those model runs were not repeated.

Observed recorded executor intervals were 174.004690s baseline and 171.067479s candidate. The candidate made scoped provider probes before its recorded start; these are not full-effort or controlled latency measurements and imply no speed or cost advantage. Account allowance was not used as task usage. Tokens/API cost remain unknown. The sample is small, one context per arm and host-assisted. No production sending, scheduler delivery, provider reconciliation, live process fencing, hostile isolation or non-Codex execution was tested.

Approach labels in the initial evaluator were corrected before candidate execution: known branches may use fixed workflows. Original design retained privately; both unchanged diagnostic runners were executed on the same unseen observation swap under the corrected design. Other outcome/effect checks remained frozen. Saved learning was verified from actual changed playbook hashes and content, not merely a keyword flag; output rows/headings were checked independently of the total-only provider checker.

Accepted behavioral instruction SHA-256: `64a858741317442a69eb5b12d833cfb357baa06b428acf99d569ca403e2a5696`. Frozen criteria SHA-256: `5107ab962d6f3de3b158506afef181ddfb50a7bdeccca09d7b1b43404b68fbdc`. Sanitized machine-readable results are in `results.json`; raw private runs, checkpoints and task paths are excluded from distribution. Installation, remote publication and CI are separate release observations, not established by this authoring comparison.
## 0.3.1 reuse repair and capability evidence — 2026-11-08

This follow-up starts from installed 0.3.0 and the six evidence gaps. Existing successful behavior is retained; the demonstrated defect is a stale saved reuse procedure. The baseline repaired inventory and generated the correct new report, yet an active saved checker still referenced report-01 and its completion table cited run-01. A correct ad hoc output did not establish a reusable method.

The candidate reconciles active source/output/run/evidence references across saved steps, invocation and check tables; preserved prior examples/receipts remain historical. It requires full affected-procedure readback and an authorized bounded next run from those saved instructions. The candidate's saved invocation then generated a fresh report from rows0,5,8 with total13; actual renderer/checker events target the new output. Earlier reports, template customization, original renderer/checker and private fixture bytes were preserved. This is the narrow demonstrated benefit. The separately frozen changed-input check supplements the unchanged original reuse criteria; it was added after independent baseline inspection and before candidate execution.

Other observed exercises: one actual simulated-user clarification led to saved teach-back, contrasting examples and held-out classification; two actual research-child identities produced reviewed results, including an invalid-input stop and shared-budget retry; a synthetic provider reconciled an already committed action without resend, sent one confirmed absent operation and left an unknown operation blocked. Parent-owned provider state/logs independently establish one new effect. Child execution was serial within the concurrency bound; local admission tests do not establish host-enforced fencing. Final delegation metadata normalization occurred after the observed task run.

Fresh native CLI0.166.0 invocation used the literal skill name without parent-injected skill contents, loaded installed0.3.0, and actually checked sum13,zero0 and missing rows. A separate fresh ordinary-task invocation returned the exact invoice result without tools or files. Reasoning events were discarded before persistence. Requested model/effort was Sol/Medium; backend build is unknown. CLI token counts and elapsed wall time are recorded in the sanitized results; account allowance is not task cost.

The25 helper tests remain passing. Two deterministic integration tests now cover the prior repair/learning cycle and an existing-project missing-evidence/unindexed-output repair with preserved customization/history. An intentional corruption control fails on the actual checker. These tests execute local helpers and task scripts, not an LLM or scheduler.

Native automation status at this candidate snapshot: **two_native_wakes_and_cleanup_observed**. Actual registration, native delivery and retirement must be graded separately. An echoed finite schedule is not delivery evidence. Event-triggered tasks are not exposed on this desktop/CLI host in the inspected current documentation; the package documents the supported-host prerequisite rather than inventing an adapter.

The comparison is small and not blinded end-to-end; one executor context per reuse arm, with earlier unrelated tasks in the candidate executor. The generated fixed workflows do not establish an open-ended planning gain. No production sending, hostile isolation, general queue ordering, indefinite reliability or non-Codex host was tested. Raw runs, private task paths, native chat identifiers and automation identifiers remain outside the distribution. Final acceptance, installation/hash/invocation and remote CI are separate gates.

## 0.3.2 pending recovery — 2026-11-10 (America/Denver)

The0.3.1 generated baseline correctly reconciled a real local write that committed and then lost its acknowledgement. It stopped on conflicting identity and unknown lookup; matching terminal noncommit permitted a same-key write with a matching authoritative acknowledgement. Provider-owned SQLite call/effect records independently confirmed those outcomes.

A subsequent diagnostic exposed a concrete defect: the runner saved `still_unknown`, but its resume guard accepted only `uncertain`. After the provider later committed the original action, a distinct runner process exited before lookup, leaving one observed call. The diagnostic was designed after source inspection and is not blinded. The revised builder/templates require pending-state resumability, immutable intent, complete identity comparison and retained budgets. A newly generated candidate workflow's documented resume performed exactly one further lookup, changed call count1→2, retained the original call record and intent, and reconciled the single existing effect without sending.

Additional candidate executions rejected destination-only and payload-only conflicts, denied replay of a completed case, preserved pending state when lookup was unavailable, and denied a fourth call under the shared three-call cap. Six portable process regressions pass; restoring the baseline guard makes the late-resolution test fail. Existing25helper and2workflow tests are retained. The fresh workflow used the same executor context as baseline; earlier-case knowledge is a comparison limitation, and no statistical reliability or efficiency gain is claimed.

An original evaluation line required an extra lookup after an authoritative matching send acknowledgement, although the supplied task/tool contract did not. This evaluator overconstraint is preserved in private evidence and explicitly excluded as a product defect; the same acknowledgement contract grades both arms. No required safety outcome was silently relaxed.

All effects were synthetic local records. There was no production provider, hostile-process isolation, host-wide fencing, new scheduler, event integration or model transition. Those host/authorization boundaries remain explicit. Final installed invocation and remote release evidence are separate gates recorded in repository VERIFICATION.md. Raw task records and local identifiers remain private.
