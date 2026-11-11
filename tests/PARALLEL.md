# Parallel source-audit regression

The test recreates the fixed CSV and JSON source-audit task in a temporary directory. Its task tools are copies of the tools used by the generated workflow. The test runs two real Python subprocesses, waits for their source-bound ready receipts, and releases them through the parent entrypoint. Host status records and handles in this test are explicitly synthetic local fixtures. The observed overlap applies to local subprocess lifetimes. Native worker qualification has separate evidence.

Run the suite from the repository root with Python 3.9 or later:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_parallel_workflow.py -v
```

The suite exercises unchanged ledgers on zero, depth, duplicate, cap-one, cap-two and exhausted-budget refusals. It checks that a missing field stops the probe while valid zeros survive normalization, a pending reservation retains its original handle, and integration rejects stale results. The test independently parses the source files and computes totals and cost per unit. The changed-input run consumes the last two of five cumulative reservations and preserves the primary artifacts.

The following control weakens the active-child guard only in a temporary copy. It should exit 1 when the cap-one check detects the extra reservation:

```sh
AGENT_FORGE_TEST_WEAKEN_ACTIVE_CAP=1 PYTHONDONTWRITEBYTECODE=1 python3 tests/test_parallel_workflow.py ParallelWorkflow.test_overlap_active_caps_and_pending_handle -v
```

The release check uses POSIX process liveness and same-host monotonic timestamps. Tests that exercise release are skipped on non-POSIX hosts. The fixture needs a temporary filesystem that supports hard links for exclusive artifact publication. The suite qualifies the local task protocol and arithmetic for the supplied inputs. Native status, host fencing, distributed delivery, simultaneous model inference and performance require their own evidence.
