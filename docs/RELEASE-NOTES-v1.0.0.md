# BYOT-CPS v1.0.0 release notes

## Public/private boundary

This release reproduces the declared GNS3 topology, benign Ubuntu Docker hosts,
pfSense installation shape and interface mapping, and the synthetic public
pfSense configuration. The baseline enables internal Unbound DNS, and each
container entrypoint selects its segment gateway as resolver. It excludes
original VM overlays, mutable guest state,
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

On 2026-10-02, the staged v1.0.0 candidate passed `make release-check` with
110 unit tests, syntax and static analysis, secret and Dockerfile scans, three
container builds, deterministic SBOM comparison, runtime policy assertions, and
inspection of all 78 source-archive files. The deterministic minimal
reproduction archive contains 47 files required by end users; development tests
and CI policy remain in the source repository for auditability. While the
repository is private, the self-referential v1.0.0 release URL is excluded
from anonymous link checking and is instead verified through the GitHub API when
the release is created. The remaining 58 links passed.

An earlier baseline passed `IOT_INTERFACE=docker0 make live-release-check` for
compromised-IoT counts 0, 1, 3, and 10. The staged HOST-ACCESS and DNS changes
have not yet received a live GNS3/pfSense DNS test. That live gate, exact-commit
hosted CI, and a clean-clone check remain mandatory before tagging. The hosted
run URL and verified commit identifier belong in the GitHub release record.

## Repository history

The public repository begins with a single root snapshot rather than the prior
development history. Contributors should use their own configured public Git
identity.
