# Changelog

All notable BYOT-CPS changes are recorded here. The project follows semantic
versioning.

## [Unreleased]

## [1.0.0] - 2026-09-04

### Added

- First public-release baseline with a declared public/private boundary,
  portable artifact acquisition, deterministic configuration media, pinned
  container inputs, governance documentation, and automated release gates.
- Public repository metadata, release notes, branch-protection requirements,
  and a documented final-release checklist.

### Security

- The release contains only benign lab hosts and a synthetic pfSense baseline;
  private overlays, operational malware, credentials, certificates, and vendor
  installer media remain outside Git.

## [0.19.0] - 2026-09-03

### Added

- Public pull-request CI for data, unit, whitespace, link, secret, Python,
  Dockerfile, container-runtime, SBOM, and source-archive checks.
- A single `make release-check` command with fail-closed summaries.
- A separate live GNS3 release gate covering compromised-IoT counts 0, 1, 3,
  and 10 with status readback and cleanup verification.

## [0.18.0] - 2026-09-03

### Added

- Reader-oriented architecture and security-boundary documentation.
- Contribution, security, citation, issue, and pull-request guidance.
- Tested-platform and maintainer-support expectations.

### Changed

- Restructured the README around purpose, safety, architecture, and a quick
  demonstration.

## [0.17.1] - 2026-09-03

### Fixed

- Made GNS3 template comparison bidirectional so obsolete fields cannot pass
  silently.
- Added migration failures when GNS3 preserves an undeclared stale field.

## [0.17.0] - 2026-09-03

### Added

- Pinned Ubuntu package snapshots, deterministic container credentials, tracked
  SPDX SBOMs, and runtime policy tests for all three lab images, including
  default-gateway DNS selection.
- Reproducible public pfSense-drive extraction and semantic comparison tests.

## [0.16.0] - 2026-09-03

### Added

- Practical Netgate installer acquisition, SHA-256 verification, local blank
  qcow2 generation, and artifact preparation commands.

## [0.15.0] - 2026-09-03

### Changed

- Removed developer-specific paths and parameterized host inputs.

## [0.14.0] and earlier

Earlier releases established the clean-clone manual, SSH-enabled benign Ubuntu
containers, deterministic pfSense configuration media, role-based names,
configurable compromised-IoT count, the BYOT-CPS namespace, and the original
portable topology exporter.
