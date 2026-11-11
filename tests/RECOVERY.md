# Generated runner recovery regression

The generated baseline stopped on an unknown provider lookup and saved `still_unknown`. Its resume guard accepted only `uncertain`, so a later process rejected the saved intent before looking up a matching commit. The fixture runner preserves the baseline behavior and allows recovery from either pending state. Its provider path is supplied through `AGENT_FORGE_TEST_PROVIDER` and subprocesses use the test interpreter. The local provider is the exercised SQLite fixture with `AGENT_FORGE_TEST_PROVIDER_STATE` selecting temporary storage. The parent fixture can supply a later matching commit and inspect call and effect records independently of the runner.

Run with Python 3 on a host that supports directory fsync. The test creates its own temporary state and starts each runner and provider call as a separate process.

```sh
python3 test_recovery_workflow.py -v
```

To reproduce the baseline failure, restore the old guard in a temporary copy for the late-resolution test. The following command is expected to exit 1 at the second runner invocation with `existing state does not authorize this transition`.

```sh
AGENT_FORGE_TEST_LEGACY_GUARD=1 python3 test_recovery_workflow.py RecoveryWorkflow.test_unknown_later_resolution -v
```

The regression covers lost acknowledgement after commit, separate process readback, target-only and payload-only mismatches, later resolution of a pending unknown, exhausted provider call budget, unavailable lookup, and matching acknowledgement after a same-key write following terminal noncommit. All effects are synthetic local records. The fixed runner demonstrates the diagnosed code correction. A separately generated workflow is needed to assess adoption of the skill instructions.
