# Reproducibility and public-release boundary

## What this repository represents

BYOT-CPS declaratively represents:

- the GNS3 node-and-link topology, adapter assignments, switch ports, and node
  placement;
- GNS3 template payloads for the pfSense firewall and Ubuntu-based lab
  containers;
- Dockerfiles and startup behavior for benign container hosts;
- a synthetic public pfSense configuration with four declared interfaces,
  lab-only addresses, DHCP pools, and basic outbound rules;
- deterministic generation of the pfSense configuration-restore drive; and
- structural, transformation, and temporary-project smoke tests.

External installer acquisition, SHA-256 verification, and local blank-disk
creation are documented in [`ARTIFACTS.md`](ARTIFACTS.md).

Container base images, the `20260903T000000Z` Ubuntu package snapshot, exact
installed package versions, SPDX SBOMs, and runtime policy checks are documented
in [`CONTAINERS.md`](CONTAINERS.md). The runtime gate verifies the expected
Ubuntu version and user, password-protected sudo, SSH policy, required tools,
allowed processes and listeners, and bounded suspicious-file indicators.

## What it does not represent

The public release does not contain or reproduce:

- linked-clone overlays or mutable state from the source virtual machines;
- software, accounts, web content, or services installed interactively in the
  source guests;
- operational bot, command-and-control, exploit, or malware payloads;
- production credentials, password hashes, certificates, private keys, VPN
  material, or firewall policy; or
- vendor installer media, operating-system images, or other artifacts whose
  distribution is controlled by third parties.

Node names such as `C2-SIMULATOR`, `RED-TEAM-HOST`, and
`COMPROMISED-IOT-NN` describe intended lab roles only. The corresponding
containers are plain Ubuntu lab hosts and do not implement harmful behavior.

## Public and private pfSense inputs

The default build uses `config/pfsense-public.xml`. This tracked configuration
is synthetic and intentionally contains only documented lab data and the dummy
`admin` / `admin` credential. The validator permits the tracked public file to
be readable while rejecting known certificate, private-key, token, and
non-dummy administrator material.

A private deployment may override the default:

```bash
PFSENSE_CONFIG=/secure/path/config.xml make pfsense-config-drive
```

Private input must be mode `600` or stricter. It remains the operator's
responsibility to keep that input and the generated restore media out of source
control and to verify that any resulting firewall policy is safe for the
attached networks.

## Security boundary

BYOT-CPS is an experimental testbed with public dummy credentials. Run it only
on isolated lab networks. Do not attach production, Internet-facing, or
untrusted host interfaces without reviewing the generated topology and
firewall policy. The public baseline permits outbound IPv4 traffic from the
three internal segments; it is not a hardened production firewall policy.

## Meaning of reproducible

For this project, reproducible means that declared inputs produce the same
portable topology and deterministic configuration media. It does not mean that
vendor downloads, package repositories, interactive installation, or
unrepresented guest state are recreated byte-for-byte. External artifacts must
be acquired separately and verified against the repository manifest.

## Runtime verification

On 2026-09-03, the public baseline was tested with the Netgate Installer
v1.1.1 and pfSense CE 2.8.1 in an isolated temporary GNS3 project. The
installer detected `/config/config.xml`, completed installation and restore,
and the installed disk booted successfully. The management WebGUI returned
HTTP 200 over HTTPS at `192.168.99.1`, and the documented `admin` / `admin`
login was confirmed manually. The temporary project, template, configuration
image, and test VM were removed afterward.

This verification establishes restore, boot, interface addressing, HTTPS
WebGUI availability, and login. DHCP lease issuance and traffic-policy behavior
were not exercised in that run and remain separate integration-test targets.
