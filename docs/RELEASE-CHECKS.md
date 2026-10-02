# Release quality gates

BYOT-CPS separates portable pull-request checks from the live GNS3 release test.
The public CI workflow never receives GNS3 server credentials and does not attach
host interfaces.

## Public pull-request CI

Every pull request runs `.github/workflows/ci.yml` with read-only repository
permissions. Its static job checks:

- every tracked JSON and XML file;
- all unit tests;
- changed-line whitespace with `git diff --check`;
- local and external Markdown links;
- tracked source for secrets;
- Python syntax and Ruff static analysis;
- both Dockerfiles with Hadolint; and
- a source archive for private paths, generated disks, captures, logs, archives,
  credentials, private keys, unsafe member types, and oversized members.

A separate container job builds all three digest-pinned Ubuntu images,
regenerates the SPDX package inventories, compares them with the tracked SBOMs,
and exercises the runtime security policy. Third-party actions and quality-tool
container images are pinned by immutable commit or image digest.

## Local release check

Stage the intended release tree and ensure every other non-ignored file is either
staged or removed. Then run:

```bash
make release-check
```

This one command runs every local, non-destructive gate: semantic topology and
data validation, all unit tests, staged and unstaged whitespace checks, local
and external Markdown links, Python syntax and static analysis, workflow
linting, secret scanning, Dockerfile linting, source-archive inspection,
deterministic reproduction-archive construction, deterministic SBOM comparison,
container builds, and runtime policy assertions including default-gateway DNS.

The command downloads pinned quality-tool and base-container images when they are
not already available. It does not create or alter a GNS3 project. Success ends
with:

```text
RELEASE CHECK: PASSED
```

Any failed subcommand ends with `RELEASE CHECK: FAILED` and a nonzero status. Do
not tag or publish that tree.

## Minimal reproduction archive

Build the end-user bundle with:

```bash
make reproduction-archive
```

The generated `dist/byot-cps-v1.0.0-reproduction.tar.gz` contains only the
declared topology and template inputs, runtime builders, required documentation,
licenses, citation metadata, and SBOMs. It deliberately excludes development
tests, CI configuration, maintainer quality tools, and release-process records.
The release test builds it twice to enforce byte reproducibility, checks the
exact allowlist and embedded `REPRODUCTION-MANIFEST.sha256`, then runs the
extracted bundle's `make validate` and `make pfsense-config-validate` targets.
Attach this bundle—not the larger source archive—as the end-user release asset.

## Live GNS3 maintainer check

The live gate is intentionally separate because a public hosted runner does not
have the installer, QEMU image directory, Docker/GNS3 integration, or an isolated
host interface. Run it on an isolated maintainer host or dedicated self-hosted
runner that satisfies `QUICKSTART.md`:

```bash
IOT_INTERFACE=docker0 make live-release-check
```

The target performs image verification, builds the containers and deterministic
pfSense configuration drive, reconciles all semantic GNS3 templates, and reads
them back. It then creates complete temporary projects with compromised-IoT
counts 0, 1, 3, and 10. For each project it verifies node/link and type counts,
checks the pfSense configuration drive, starts the firewall and every Docker
node, reads their statuses back, and deletes the project in `finally`.

The runner checks after every count that no temporary projects remain. A
successful run ends with:

```text
LIVE GNS3 RELEASE CHECK: PASSED (counts 0, 1, 3, 10; no temporary projects remain)
```

If a run is interrupted outside Python's normal exception handling, inspect the
GNS3 project list manually and remove only projects whose names begin with
`byot-cps-smoke-` after confirming they are disposable test projects.

## Release decision

A release is eligible for a tag only when:

1. public CI is green for the exact proposed commit;
2. `make release-check` passes for the exact staged tree;
3. `make live-release-check` passes on a clean isolated test host; and
4. the working tree is clean after the release commit.

Record the commands, test count, live topology counts, and remaining limitations
in the release notes.

## Version 1.0 final gate

Before creating the public release, verify all of the following against the
same release commit:

1. a clean clone on an independent hosted runner passes both public CI jobs;
2. tracked files contain no private files or identifying paths;
3. GitHub detects the MIT license and the release archive passes
   `src/inspect_archive.py` plus manual member review;
4. all three Docker images build and pass their runtime and SBOM checks,
   including the DMZ Nginx listener and HTTP response;
5. the public pfSense configuration drive builds twice with the same digest and
   semantically matches `config/pfsense-public.xml`;
6. the live GNS3 gate passes for counts 0, 1, 3, and 10 without leftovers;
7. the release commit has a clean working tree; and
8. an annotated `v1.0.0` tag points to that verified commit.

Do not create or publish the tag while any item is missing. Record the local
command results, live-test outcome, archive result, and remaining interactive
limitations in `docs/RELEASE-NOTES-v1.0.0.md`. Record the exact release commit
and hosted run URL in the GitHub release record so adding the URL does not alter
the commit that CI verified.

While the repository is private, anonymous link checking excludes the
self-referential v1.0.0 release URL. At release creation, verify the tag, target
commit, publication state, and release URL directly through the GitHub API
before changing repository visibility.
