# Local resource ownership and bounded delegation

Choose the authority that owns the effect. Use its atomic conditional write or transaction to check ownership and commit. A lease file, a process-local lock, or a check before a separate write leaves a race. Use a supported durable store shared by the relevant writers. Keep a single authorized writer when you cannot verify atomic enforcement.

## Fence a resource write

The optional [local resource helper](../scripts/local_resource.py) uses Python 3.9+ and SQLite on one supported local filesystem. It owns a signed safe-integer counter per resource. It illustrates transactional fencing for that counter and its operation receipt. For a different resource, implement equivalent enforcement where that resource writes. Owner strings label cooperative writers. Use the host's permissions for access control.

Invoke `python3 scripts/local_resource.py --db PATH ACTION` with one JSON object on standard input:

| Action | Input fields | Result |
|---|---|---|
| `claim` | `resource`, `owner`, `ttl_ms` | `claimed` with `token` and `expires_at_ms`, or `busy` |
| `release` | `resource`, `owner`, `token` | `released` or `stale` |
| `apply` | `resource`, `owner`, `token`, `operation_key`, `delta` | `committed` or `replayed` with the original operation value and token, or `stale` / `conflict` |
| `lookup` | `resource`, `operation_key`, `delta` | `committed` with the original receipt, `unknown`, or `conflict` |
| `read` | `resource` | `present` with value, current token, owner and expiry, or `unknown` |

Statuses exit 0. Invalid inputs, storage errors, and lock timeouts exit 2. Claim TTL uses local wall-clock time, from 1 ms to 24 hours. A new claim advances the fence without resetting the value. Ownership, expiry, update, and the receipt are checked or recorded in one write transaction. Releasing or expiring a lease leaves the fence and receipts intact. Use a stable resource and operation key for the same integer delta. An active newer owner may replay the original result. Stale writers must use readback for a lost acknowledgement.

To qualify this pattern, use independent processes. Give A a fence, let it expire or release it, give B a newer fence, and have A attempt the effect while B owns the resource. Inspect the authoritative value and operation ledger after the rejection. Exercise a lost acknowledgement with a later read of the original key and exact identity. Check that conflicting input never commits. Use fresh changed input and an independent expected value for the saved-procedure rerun. Local SQLite evidence covers the selected file and helper transaction. Distributed clocks, network filesystems, external effects and hostile writers require their own implementation and verification.

## Reserve a child launch before admitting it

Freeze the authority, budget, deadline, maximum depth, active concurrency and total workers at the parent boundary. Give each allowed child a concrete input identity, scoped tools, a result contract and an owner. Persist a reservation before dispatch. Evaluate the shared limits and reserve within one transaction. Zero depth, concurrency, or worker allowance disables dispatch. Duplicate keys reuse the original reservation, and changed identity conflicts. A terminal result can release an active slot while total consumed launches remain charged.

Disable direct, deferred and default launch paths that would bypass the gate. Inspect the actual parent and child capabilities, including framework defaults. In Eve, confirm the selected version's support for disabling root-copy/default tools and hiding the declared child from model calls while a single authorized workflow can open it. Avoid giving the child the launch workflow. An instruction alone does not enforce scope.

Bind the reservation to the authoritative parent session and call. Preserve the child-session and delivery handles exposed by the runtime. If admission or the return remains unknown, keep the original reservation active and read back that operation. Missing readback leaves it pending. Check terminal child status, source identity and result before integration. Replay an integrated return without repeating the effect. Use distinct real sessions to verify an allowed launch, cross-session concurrency denial, disabled/depth/exhaustion cases, and recovery of an uncertain return. Record exactly which layer enforced each limit.

Recovery may assign a different call ID to an interrupted step. Correlate results with the original run, the actual tool, and validated input; do not assume a generated call label survives restart. Test that the recovered child reaches a terminal state, and separately verify idempotency for any protected effect. A pure tool may legitimately run again after interruption.
