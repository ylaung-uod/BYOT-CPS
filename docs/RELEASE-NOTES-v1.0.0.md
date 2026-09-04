# BYOT-CPS v1.0.0 release notes

## Public/private boundary

This release reproduces the declared GNS3 topology, benign Ubuntu Docker hosts,
pfSense installation shape and interface mapping, and the synthetic public
pfSense configuration. It excludes original VM overlays, mutable guest state,
operational malware, production credentials, certificates, private host
configuration, proprietary guest content, and vendor installer media.

## External artifacts

The Netgate Installer is not redistributed. Obtain the exact supported archive
through Netgate's official workflow, place it at the path documented in
`docs/ARTIFACTS.md`, and run `make prepare-images` followed by
`make verify-images`. The manifest records the compressed and expanded SHA-256
digests. A blank pfSense disk and configuration drive are generated locally.

## Supported versions

The verified baseline is Ubuntu 22.04.5 LTS on x86-64, GNS3 2.2.55, Docker
29.2.1, QEMU 6.2.0, Python 3.10.12, Git 2.34.1, pfSense CE 2.8.1, and Netgate
Installer 1.2. Support is limited to the latest tagged BYOT-CPS release and the
benign, isolated lab boundary described in `SECURITY.md`.

## Dummy credentials

The lab images intentionally use documented dummy credentials for local
training. They are password-protected but are not production-safe. Do not
attach the testbed to production networks or reuse these credentials elsewhere.

## Interactive pfSense installation

The Netgate Installer remains an interactive, network-dependent vendor workflow.
The release prepares and verifies its inputs but does not automate vendor login,
license acceptance, release selection, installation, or the first boot. A
started QEMU process alone does not prove installation or configuration restore.

## Verification results

On 2026-09-04, the staged v1.0.0 candidate passed `make release-check` with
91 unit tests, syntax and static analysis, secret and Dockerfile scans, both
container builds, deterministic SBOM comparison, runtime policy assertions, and
inspection of all 71 source-archive files. The first external-link attempt
encountered three vendor-site timeouts; an unchanged retry passed all 44 links.

The same candidate passed `IOT_INTERFACE=docker0 make live-release-check` for
compromised-IoT counts 0, 1, 3, and 10. Every temporary project was read back,
started, deleted, and confirmed absent. The Phase 6 hosted baseline passed both
jobs at <https://github.com/ylaung-uod/byot-cps/actions/runs/33817058239>.
Exact-commit hosted CI and a clean-clone check remain mandatory before tagging;
their resulting URLs and commit identifier belong in the GitHub release record.

## Commit attribution

The existing history is preserved rather than rewritten. Its commits are
attributed to `Hermes Agent <hermes-agent@localhost>`. This attribution is
accepted for the public v1.0.0 history; future contributors should use their own
configured Git identity.
