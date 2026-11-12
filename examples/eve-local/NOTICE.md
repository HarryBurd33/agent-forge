# Fixture provenance

Original Agent Forge fixture logic follows the repository MIT license. The package configuration and TypeScript configuration began with the Eve 1.0.0-rc.9 scaffold and were modified for a private, deterministic local test application. Apache-2.0 terms and upstream notices are retained in LICENSE-APACHE-2.0 and UPSTREAM-NOTICE. Eve and its dependencies are installed from the registry and are not vendored here. The fixture is not a production template.

The browser source, ownership gateway and cancellation tool are original MIT fixture code. The browser UI imports the SDK from the installed Eve 1.0.0-rc.9 dependency (Apache-2.0). The build uses the pinned Rolldown 1.2.16 development dependency (MIT, https://github.com/rolldown/rolldown), already present in the Eve lock graph. The lockfile records tarball versions and integrity for both. The ignored generated bundle is for local testing; it is not redistributed with these source files.

The optional local fixture pins just-bash 3.6.0 (Apache-2.0, https://github.com/vercel-labs/just-bash). Its actual installed LICENSE and locked package integrity were inspected. It is installed from the registry, not vendored into this source export. The two sandbox configurations use the version-matched Eve public API and retain the existing Apache attribution.
