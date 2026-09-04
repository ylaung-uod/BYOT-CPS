# BYOT-CPS v1.0.0 reproduction bundle

This bundle contains the files needed to recreate the safety-bounded BYOT-CPS
GNS3 topology. Development tests, hosted-CI configuration, contribution files,
and maintainer release records remain in the source repository and are not part
of this end-user package.

## Reproduction boundary

The bundle recreates the declarative topology, GNS3 templates, pinned Ubuntu
containers, public pfSense configuration media, and physical-interface boundary.
It does not include the Netgate installer, proprietary media, original VM
overlays, mutable guest state, private experimental data, credentials, captures,
or operational attack payloads.

Read [the reproducibility boundary](docs/REPRODUCIBILITY.md),
[artifact instructions](docs/ARTIFACTS.md), and
[safety boundary](docs/SECURITY-BOUNDARY.md) before connecting an interface.

## Verify the bundle

From the extracted `byot-cps-v1.0.0` directory, verify every packaged file:

```bash
sha256sum -c REPRODUCTION-MANIFEST.sha256
make validate
make pfsense-config-validate
```

## Host prerequisites

The tested baseline uses Linux, GNS3 2.2.55, Docker, QEMU/KVM, Python 3.10 or
newer, GNU Make, `qemu-img`, `sfdisk`, `mkfs.vfat`, and mtools. Docker must work
without `sudo`. See the [complete quick-start](QUICKSTART.md) for installation
commands and troubleshooting.

## Acquire the external installer

The Netgate installer is not redistributed. Display the pinned filename,
checksums, official acquisition URL, and license URL with:

```bash
make fetch-help
```

After completing the vendor workflow, save the archive as
`downloads/netgate-installer-v1.2-RELEASE-amd64.iso.gz`, or pass its location
with `PFSENSE_INSTALLER_ARCHIVE`.

## Recreate the templates and topology

Start the local GNS3 server, then run:

```bash
make prepare-images
make verify-images
make templates
IOT_INTERFACE=docker0 make topology
make smoke-test
```

The `make reproduce` target performs template and persistent-topology creation
in one dependency chain. The default generated project is `byot-cps`; it will
not overwrite an existing project.

Important configurable variables include:

- `GNS3_SERVER_CONFIG`
- `GNS3_QEMU_IMAGES`
- `PFSENSE_INSTALLER_ARCHIVE`
- `QEMU_PATH`
- `IOT_INTERFACE`
- `PROJECT_NAME`
- `COMPROMISED_IOT_COUNT`
- `PFSENSE_CONFIG`

The default topology contains 16 nodes and 15 links, including three
compromised-IoT role containers. For a pool size `N`, it contains `13 + N` nodes
and `12 + N` links.

## Optional container verification

To rebuild both containers and verify their tracked SBOMs and runtime policy:

```bash
make phase4-verify
```

See [container reproducibility](docs/CONTAINERS.md),
[architecture](docs/ARCHITECTURE.md), and the
[pfSense configuration guide](pfsense/README.md) for details.

## Safety, licensing, and citation

This lab uses public dummy credentials and must remain isolated from production
and untrusted networks. Report vulnerabilities according to
[SECURITY.md](SECURITY.md). BYOT-CPS is distributed under the
[MIT License](LICENSE); third-party terms are summarized in [NOTICE.md](NOTICE.md).
Citation metadata is provided in [CITATION.cff](CITATION.cff).
