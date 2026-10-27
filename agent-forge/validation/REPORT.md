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

Two helper bugs were reproduced independently. A temporary exclusion `outputs/reports` hid an unindexed durable file; the fix rejects protected durable roots and descendants. Missing optional scheduler access incorrectly blocked a ready manual project; the fix warns about optional absence while required/undeclared missing support still blocks. Original held-out fixtures were rerun independently: the first now fails audit, the second passes with the optional warning. The helper never claimed domain/content validation; an independently observed stale input hash still passes structural audit and requires actual source-version/outcome checks by the runner.

The initial candidate ran before two supporting references were written. It accurately reported the missing files. Both now exist and were independently inspected. Historical outputs retain the limitation. Initial A1 run-record field omissions and Q1 review-only learning prompted explicit saved-playbook/diff and per-check field inspection instructions. Supplemental execution is reported separately rather than rewriting initial results.

## Executed deterministic checks

The helper suite currently has **14 passing CLI tests**: initialization and preservation, traversal/symlink handling, real index retrieval, missing files/unindexed outputs/missing evidence, explicit zero versus absent/invalid limits, ID/dependency/step errors, explicit external references, temporary-root and nested-root inventory protection, claimed registration receipts, draft versus readiness markers, optional versus required missing capabilities and malformed JSON/types. Tests verify the helper's local contract; they do not establish arbitrary outcome quality, credentials absence, scheduler truth or live host enforcement.

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

Global installation/native discovery; a separate CLI model task; real scheduler registration or recurring/event delivery; actual domain connector work; external messaging/provider reconciliation; live overlapping process fencing; non-Codex host execution. No artifact or descriptive schedule supplies these capabilities or their authorization. Python 3.9 is the declared minimum; tests ran on the available Python interpreter, not every supported release.
