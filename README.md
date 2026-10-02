# BYOT-CPS: A Hybrid IoT/CPS Security Testbed for Experimentation and Platform Evaluation

## Purpose

BYOT-CPS rebuilds a 17-node cyber-physical security lab from declarative files
and the GNS3 2.2 REST API. It provides a pfSense firewall, four network segments,
benign Ubuntu diagnostic containers, a configurable compromised-IoT pool, exact
link assignments, a route-gated Nginx service on the DMZ web server,
pfSense-provided DNS for internal containers, checksummed external inputs,
deterministic configuration media, tracked container SBOMs, and automated
verification.

The repository reproduces topology and declared appliance inputs. It does not
reproduce the approximately 93 GiB of mutable guest state from the source
project's linked-clone overlays.

## Accompanying paper

BYOT-CPS is the public, safety-bounded reference implementation accompanying
the BYOT-CPS research paper:

- [Paper on arXiv](https://arxiv.org/abs/2605.23059)
- [Paper DOI](https://doi.org/10.48550/arXiv.2605.23059)
- [BYOT-CPS v1.0.0 software release](https://github.com/ylaung-uod/byot-cps/releases/tag/v1.0.0)

The paper presents and evaluates the complete hybrid IoT/CPS testbed. This
repository publishes its reproducible virtual core and physical-device
integration boundary. Physical devices, proprietary media, mutable guest
state, private experimental data, and operational attack payloads are not
included.

If you use the architecture or evaluation, cite the paper. If you use or
modify the template, also cite the software release. Machine-readable citation
metadata is provided in [`CITATION.cff`](CITATION.cff).

## Safety boundary

This is an experimental lab with public dummy credentials. Keep it isolated from
production and untrusted networks. The containers contain no operational bot,
C2, exploit, scanner, or malware payload. Role names describe topology positions
only.

Do not publish private pfSense configurations, real credentials, proprietary
images, captures, overlays, or live malware. Maintainers do not support
operational malware deployment or unauthorized access.

Read [`docs/SECURITY-BOUNDARY.md`](docs/SECURITY-BOUNDARY.md) before attaching a
physical host interface. Report vulnerabilities using [`SECURITY.md`](SECURITY.md).

## Architecture

The default topology contains one pfSense QEMU firewall, one GNS3 NAT node, four
Ethernet switches, nine Ubuntu Docker containers, two host-interface cloud
nodes, and 16 links. The network segments are:

| Segment | pfSense adapter | Address | Main roles |
|---|---:|---|---|
| WAN | `em0` | DHCP | ISP, external client, C2 simulator |
| Management | `em1` | `192.168.99.1/24` | management administrator |
| DMZ | `em2` | `172.20.0.1/24` | web server |
| CPS | `em3` | `10.0.0.1/24` | operator, IoT interface, red-team host, compromised-IoT pool |

For a pool of `N` compromised-IoT containers, the project has `14 + N` nodes
and `13 + N` links. The default is three; zero and larger values are supported.
`IOT_INTERFACE=docker0` is the portable IoT default. `MGMT_INTERFACE=byot-mgmt`
selects a dedicated host-only TAP connected only to `MGMT-SWITCH`, allowing the
host browser to reach the pfSense WebGUI at `https://192.168.99.1/`.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the topology, interface
model, exact ports, component layers, and build flow.

## Quick demonstration

Install the host prerequisites, obtain the Netgate installer as described by the
artifact guide, and run:

```bash
git clone <repository-url> byot-cps
cd byot-cps
make validate
make fetch-help
make prepare-images
make templates
sudo ip tuntap add dev byot-mgmt mode tap user "$USER"
sudo ip addr add 192.168.99.2/24 dev byot-mgmt
sudo ip link set byot-mgmt up
MGMT_INTERFACE=byot-mgmt \
IOT_INTERFACE=docker0 make topology
make smoke-test
```

End users may instead download the minimal reproduction archive attached to the
GitHub release. It contains only the declarative inputs, runtime builders,
required documentation, licenses, and SBOMs. Verify it after extraction with
`sha256sum -c REPRODUCTION-MANIFEST.sha256`; development tests and CI files
remain available in the source repository for independent audit.

`make templates` verifies external images, builds the pinned containers, creates
the pfSense configuration drive, and reconciles complete GNS3 template payloads.
The smoke test creates a separate temporary project, checks 17 nodes and 16
links, starts the firewall and all containers, verifies status, and deletes the
project.

For the complete clean-clone installation, interactive pfSense restore,
container addressing, SSH setup, and troubleshooting, follow
[`QUICKSTART.md`](QUICKSTART.md).

## Reproducibility and artifacts

- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) distinguishes represented
  topology/configuration state from excluded mutable guest state.
- [`docs/ARTIFACTS.md`](docs/ARTIFACTS.md) documents vendor acquisition,
  compressed and expanded SHA-256 checksums, compatibility, and terms.
- [`docs/CONTAINERS.md`](docs/CONTAINERS.md) documents the pinned Ubuntu package
  snapshot, SPDX SBOMs, and runtime policy tests.
- [`pfsense/README.md`](pfsense/README.md) documents deterministic configuration
  media and the one-time installer workflow.

Host-specific inputs are explicit Make variables: `GNS3_SERVER_CONFIG`,
`QEMU_PATH`, `GNS3_QEMU_IMAGES`, `IOT_INTERFACE`, `PROJECT_NAME`, and
`PFSENSE_CONFIG`. No developer-specific path is required.

## Verification

In a full source checkout, maintainers run:

```bash
make release-check
IOT_INTERFACE=docker0 make live-release-check
```

Maintainers build the deterministic end-user bundle with
`make reproduction-archive`. Its default output is
`dist/byot-cps-v1.0.0-reproduction.tar.gz`.

In the minimal archive, end users can run `make validate`,
`make pfsense-config-validate`, `make phase4-verify`, and `make smoke-test`
without the source repository's development-only tests or CI configuration.

Public pull requests run the portable static, policy, unit, and container gates.
The live GNS3 gate remains a maintainer release check because it requires local
installer media and an isolated GNS3 host. See
[`docs/RELEASE-CHECKS.md`](docs/RELEASE-CHECKS.md) for the exact gate boundary,
tool pinning, cleanup behavior, and pass/fail criteria.

The public-release scope, external prerequisites, dummy credentials, supported
versions, and verification record are summarized in
[`docs/RELEASE-NOTES-v1.0.0.md`](docs/RELEASE-NOTES-v1.0.0.md).

The tested baseline is Ubuntu 22.04.5 LTS, GNS3 2.2.55, Docker 29.2.1, QEMU
6.2.0, Python 3.10.12, and Git 2.34.1 on x86-64. See
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for the tested pfSense
restore boundary and [`docs/CONTAINERS.md`](docs/CONTAINERS.md) for container
checks.

## Contributing, support, and citation

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing changes. Supported
work includes reproducibility fixes, safe topology extensions, benign defensive
tools, tests, and documentation. Security reports follow [`SECURITY.md`](SECURITY.md).
Release history is in [`CHANGELOG.md`](CHANGELOG.md), and citation metadata is in
[`CITATION.cff`](CITATION.cff).

## License

BYOT-CPS source and documentation are licensed under the [MIT License](LICENSE).
Third-party artifacts, packages, software, and marks retain their own terms; see
[`NOTICE.md`](NOTICE.md).
