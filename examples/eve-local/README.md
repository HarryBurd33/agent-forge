# Agent Forge synthetic Eve fixture

This npm app (`private: true` prevents npm publication) uses a deterministic mock model to exercise Agent Forge's runtime application guide. Follow the [playbook](PLAYBOOK.md) for installation, typed-tool and skill evals, the authenticated localhost event route, a saved session cursor, restart checks, and a one-shot dev schedule trigger.

Node 24 and a registry install of the pinned lockfile are required. The fixture uses Eve 1.0.0-rc.9 under Apache-2.0 as a dependency. It needs a synthetic local bearer token and has no model-provider key or deployment setup.

See [provenance](NOTICE.md) and the repository [validation report](../../agent-forge/validation/REPORT.md) for historical results. The toolbox starts with draft instance records; validate and record your own execution before relying on a new copy. Framework dependencies, local stores and raw traces are excluded.

The same playbook includes the shared SQLite launch budget, one declared mock child, and verification of the original child receipt after an uncertain return. The fixture uses one trusted local ledger and a synthetic bearer identity.

The optional local browser client qualifies authenticated session ownership, display reconnect, and server-turn cancellation. Follow `check-browser` in the playbook. It uses synthetic identities and a versioned SQLite ownership store shared by one or two loopback gateways with one Eve backend. The optional [ownership qualifier](PLAYBOOK.md#qualify-shared-browser-ownership-and-stopped-restore) checks cross-gateway access and stopped same-path restore.

The optional [two-world recovery check](PLAYBOOK.md#qualify-two-local-worlds-and-a-stopped-restore) runs two actual local Eve processes against one SQLite admission ledger, then verifies a stopped bundle restored at the same paths. The wrapper also provides read-only bundle verification.
