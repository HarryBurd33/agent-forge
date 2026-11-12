# Remaining qualification plan

Agent Forge 0.4.4 retains reusable local enforcement and verifies the optional runtime example. Its instructions do not create scheduler, process or provider guarantees. These gates are scoped to the actual target application; no new accounts, paid inference, production effects or permanent infrastructure were needed for this release.

| Area | What is established | Next implementation and observable acceptance | Prerequisite / remaining limit |
|---|---|---|---|
| Resource ownership | One local SQLite counter checks fence, owner, expiry, effect and receipt in a transaction; stale writers and conflicting replay rejected | For another resource, place the conditional check at that resource's write boundary; kill after commit and recover the same operation receipt | A selected resource adapter; counter evidence cannot cover an external service |
| Runtime children | Actual root and child sessions across two independent local runtime processes, atomic shared count/depth/concurrency admission, disabled direct launch paths, same-intent readback and consumed uncertain reservations | Qualify the selected production orchestrator with simultaneous sessions, denied bypasses and interrupted integration | Current fixture uses cooperative local storage and a deterministic model; no strict token/dollar cap or hostile-process isolation |
| Browser | Real browser accessed a session through a second gateway, rendered13 then held-out9, cancelled a server turn and denied another synthetic principal; shared atomic capacity, uncertain finalization and complete stopped store restoration verified | Use actual identity/session expiry and tenant roles; qualify the selected production store and revocation boundary | Two cooperative loopback gateways on one trusted local SQLite store; synthetic tokens, no production identity or cross-host replication |
| Crash recovery and migration | Complete same-version, same-path stopped bundle restoration with original history/handles is verified; local counter lost-acknowledgement recovery and runtime crash findings and exact repair boundary are recorded in VERIFICATION.md | For each effect, interrupt before/during/after commit and reconcile original identity; for an actual version upgrade, restore a backup and verify outstanding runs before and after migration | No migration target selected; a harmless interrupted arithmetic call cannot qualify external-effect idempotency |
| Cadence, replicas and isolation | Two historical native timed deliveries were observed and their pilot retired; local Eve schedule dispatch was tested separately | For a selected supported host, verify a finite recurring schedule, overlap, expiry and retirement; independently probe stale replicas and benign sandbox escape attempts | Requires that target host, shared storage and isolation boundary; no permanent scheduler, service or cross-host guarantee bundled |
| Provider authentication and events | Version-matched guidance and local authenticated event route | Implement the selected provider's credential scope, expiry, tenant checks and event delivery; verify actual receipts and uncertain outcomes; retire test registrations | Specific provider, credentials, target scope and effects authority have not been supplied; no external messages or paid API calls |
| Optional model-directed planning | Direct, fixed-workflow and evidence-dependent tool choices already have bounded examples | Pick a task where next actions genuinely require observations; compare held-out correctness, stopping, tool misuse and recorded usage against the simpler approach | Opportunity rather than a required new runtime; no framework adopted just because a tutorial uses it |

Keep candidate acceptance outside the generated agent. Preserve immutable input/operation identities, source versions, minimal tool results, failure artifacts and actual outcomes without secrets or hidden reasoning. An unavailable gate stays unverified; configuration and observed successful execution remain separate.

## Next feasible work after 0.4.2

1. For a selected real resource, adapt conditional ownership and immutable receipt checks at its write boundary, then interrupt before/during/after commit and reconcile without duplicate effects. Resource and effects authority are prerequisites.
2. For a selected production host/store, qualify cross-host ownership and consistent backup before a real version migration. Two local processes and a quiescent same-path restore do not cover those boundaries.
3. For a selected identity/event/scheduler provider, verify credentials, expiry, tenant denial, actual delivery, overlap and finite retirement. No provider or production scope is selected.
4. For a selected native isolation provider, test benign filesystem/network/process escape and resource bounds. A macOS host permission probe is not an isolation implementation or guarantee.
5. Optionally compare observation-driven planning with a simpler fixed method on a suitable held-out task; current evidence does not justify adopting another framework.

The bounded provider-free local qualification tranche is complete when installed invocation and release checks pass. No unsupported provider setup or permanent service is implied by this plan.

## Next feasible work after 0.4.3

1. Retain the verified local fixture as a regression boundary. For production browser use, choose an identity provider and persistent host/store, then implement expiry/revocation and tenant roles with actual denied reads/writes and recovery.
2. For a concrete external resource, place immutable operation identity and conditional ownership at its write boundary; interrupt before/during/after commit and reconcile without duplicate effects. Backend creation plus ownership finalization remains a two-system boundary.
3. For cross-host replicas, live backup or a version migration, select the actual deployment and qualify its complete state model. Current stopped same-path restore is a rollback method, not migration evidence.
4. Select an event/scheduler or native isolation provider before testing delivery, retirement or benign escape probes. Existing timed deliveries and local tools do not establish those guarantees.
5. A further planner/framework requires a task where evidence-dependent choices measurably beat the simpler method. No such framework is needed for this ownership fix.

These are target-dependent follow-on gates, not claims of universal capability parity. No production account, credential, API budget, permanent service or external messaging is implied.

## Next feasible work after 0.4.4

Explicit stopped conversion from the old local JSON ownership format is now qualified against original sessions and histories. The backend version and state do not change. This closes a concrete format-upgrade gap; it does not qualify a general Eve or provider migration. Production identity and expiry, cross-host storage, live backup, external-resource effects and native isolation still require selected targets and their actual acceptance runs. Preserve complete old state for rollback; never infer backend existence or identity from a valid JSON mapping alone.
