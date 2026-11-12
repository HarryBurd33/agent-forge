# Agent Forge synthetic Eve fixture

This npm app (`private: true` prevents npm publication) uses a deterministic mock model to exercise Agent Forge's runtime application guide. Follow the [playbook](PLAYBOOK.md) for installation, typed-tool and skill evals, the authenticated localhost event route, a saved session cursor, restart checks, and a one-shot dev schedule trigger.

Node 24 and a registry install of the pinned lockfile are required. The fixture uses Eve 1.0.0-rc.9 under Apache-2.0 as a dependency. It needs a synthetic local bearer token and has no model-provider key or deployment setup.

See [provenance](NOTICE.md) and the repository [validation report](../../agent-forge/validation/REPORT.md) for historical results. The toolbox starts with draft instance records; validate and record your own execution before relying on a new copy. Framework dependencies, local stores and raw traces are excluded.
