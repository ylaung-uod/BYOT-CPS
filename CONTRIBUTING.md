# Contributing to BYOT-CPS

BYOT-CPS accepts changes that improve reproducibility, portability, safe lab
operation, documentation, tests, or benign defensive capability.

## Supported contribution scope

Good contributions include:

- deterministic topology, template, image, and configuration generation;
- safe GNS3, Docker, pfSense, and host-platform compatibility fixes;
- validation, runtime assertions, SBOM quality, and test coverage;
- documentation and clean-clone installation improvements; and
- inert traffic generators or defensive monitoring that cannot autonomously
  attack third-party systems.

Do not submit credentials, private configurations, proprietary artifacts,
packet captures containing sensitive data, exploit payloads, or operational
malware. The project does not accept or support operational malware deployment,
credential theft, persistence, evasion, or unauthorized access.

## Development workflow

1. Start from the latest tagged release and create a focused branch.
2. Keep host-specific paths, credentials, generated media, and downloaded images
   outside Git.
3. Add or update tests before changing behavior.
4. Keep semantic template names and role-based node names stable unless the
   change is an intentional migration.
5. Update user documentation, manifests, SBOMs, and `CHANGELOG.md` when behavior
   or inputs change.

Stage the intended tree, then run the single local release gate:

```bash
make release-check
```

This includes the former standalone `make test` and `make phase4-verify` coverage
plus the Phase 6 policy gates.

Changes affecting topology creation or GNS3 templates should also run, on an
isolated GNS3 host:

```bash
IOT_INTERFACE=docker0 make live-release-check
```

Confirm that no `byot-cps-smoke-*` project remains after testing. Do not run a
live GNS3 test against production interfaces. The full gate definition is in
`docs/RELEASE-CHECKS.md`.

## Pull requests

Keep each pull request scoped to one change. Describe the motivation, user-visible
impact, security implications, tests executed, and any reproducibility boundary
that remains. Do not claim a live test passed unless it was actually run and its
external state was read back.

By contributing, you agree that your contribution is licensed under the MIT
License in `LICENSE`.

## Security reports

Security reports must follow `SECURITY.md`. Do not disclose a vulnerability,
secret, private configuration, proprietary artifact, or malware sample in a
public issue.
