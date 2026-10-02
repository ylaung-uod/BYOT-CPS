# Security boundary

## Intended use

BYOT-CPS is an isolated educational and defensive-testing topology. It provides
network roles, benign Ubuntu diagnostic containers, a synthetic pfSense
configuration, and reproducibility checks. It does not provide operational bot,
command-and-control, exploit, persistence, credential-theft, scanning, or mining
payloads.

The role names `C2-SIMULATOR`, `RED-TEAM-HOST`, and
`COMPROMISED-IOT-NN` describe positions in the topology. They are not claims
about software installed in those containers.

## Isolation requirements

- Run the project on a dedicated lab host or otherwise isolated environment.
- Keep `IOT_INTERFACE=docker0` unless a reviewed experiment requires a physical
  interface.
- Do not bridge the lab to production, management, safety-critical, or
  Internet-facing networks.
- Do not expose GNS3, SSH, VNC, or the pfSense WebGUI to untrusted networks.
- Review firewall rules and routes before introducing external connectivity.
- Stop the lab and disconnect attached interfaces if unexpected traffic or
  processes appear.

The public pfSense baseline permits outbound IPv4 traffic from the Management,
DMZ, and CPS segments. It also exposes recursive DNS only on those three
internal interfaces, not WAN. It is a lab policy, not a hardened production
policy.

The baseline places block rules before the DMZ and CPS pass rules to prevent
those segments from initiating connections toward management. The
`HOST-ACCESS` TAP nevertheless places the Ubuntu host directly on the same
Layer-2 segment as `MGMT-ADMIN`; use a stateful host firewall to block unsolicited
input on `byot-mgmt`. Host-initiated routed traffic can still reach other lab
segments when the operator adds a route through pfSense.

## Dummy credentials

The public build deliberately uses credentials that are visible in this
repository:

| Component | Username | Password |
|---|---|---|
| Ubuntu lab containers | `lab` | `lab` |
| pfSense public baseline | `admin` | `admin` |

These credentials exist only to make the isolated demonstration reproducible.
Never reuse them, expose them to untrusted networks, or treat them as secrets.
Root SSH login is disabled in the containers, and `sudo` requires the `lab`
password.

## Sensitive and excluded material

Never commit or publish:

- private pfSense backups, real password hashes, certificates, or private keys;
- GNS3 server credentials or configuration containing credentials;
- proprietary installer media, VM disks, linked-clone overlays, packet captures,
  or mutable project state;
- production addresses, hostnames, VPN material, firewall policy, or customer
  data; or
- live malware, exploit payloads, operational bot/C2 code, or stolen data.

Private pfSense input belongs under the ignored `secrets/` directory with mode
`600` or stricter. Generated media and downloaded artifacts remain ignored.

## Runtime safeguards and limitations

The container runtime gate verifies the expected Ubuntu version and workload
user, password-protected sudo, SSH policy, required tools, allowed listeners,
allowed service processes, the default-gateway resolver policy, and bounded
suspicious executable-name indicators.
These checks detect declared policy violations but cannot prove the absence of
all malicious behavior.

The smoke test creates a unique temporary GNS3 project, checks node/link counts,
starts the firewall and all containers, reads status back, and deletes the
project in `finally`. It does not validate every possible packet path or firewall
rule.

## Reporting and support boundary

Follow [`../SECURITY.md`](../SECURITY.md) for private vulnerability reporting.
Do not include credentials, private configurations, proprietary artifacts, or
malware samples in a public issue.

Maintainers support reproducibility defects, safe lab operation, documentation,
and benign defensive extensions. They do not support operational malware
deployment, unauthorized access, evasion, persistence, credential theft, or
attacks against third-party systems.
