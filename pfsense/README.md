# Reproducible pfSense configuration

The pfSense VM is rebuilt from three inputs:

1. `pfSense.qcow2` — locally generated blank linked-clone base disk.
2. `netgate-installer-v1.2-RELEASE-amd64.iso` — pinned installer media.
3. `pfsense-config.img` — generated FAT16 configuration drive containing `config/config.xml`.

Run `make fetch-help`, `make prepare-images`, and `make verify-images` to obtain
and prepare the first two inputs. Exact checksums and the vendor acquisition
boundary are documented in `docs/ARTIFACTS.md`.

The configuration drive follows Netgate's Configuration Restore / External Configuration Locator layout:

- https://docs.netgate.com/pfsense/en/latest/backup/restore-during-install.html

## Public configuration input

The default build uses `config/pfsense-public.xml`. It is a synthetic baseline
containing the documented lab interfaces, DHCP pools, basic outbound rules,
the Unbound DNS Resolver, and the dummy `admin` / `admin` credential. Unbound
listens on LAN, OPT1, and OPT2 and uses WAN for recursive queries. The public
configuration contains no source firewall policy, certificates, private keys,
or production identifiers.

The public rules allow management-initiated outbound traffic but block new DMZ
and CPS connections toward the management network before their general outbound
pass rules. This protects routed management hosts; peers on the management
switch remain on the same Layer-2 segment and require host-side firewalling.

For a private deployment, override the default explicitly:

```bash
install -d -m 700 secrets/pfsense
install -m 600 /secure/path/config.xml secrets/pfsense/config.xml
PFSENSE_CONFIG=secrets/pfsense/config.xml make pfsense-config-drive
```

The complete `secrets/` directory is excluded from Git. The validator rejects
a group- or world-readable private configuration. The tracked public input is
allowed to be readable only after checks reject secret-bearing elements and a
non-dummy administrator hash.

## Validate and build

```bash
make pfsense-config-validate
make pfsense-config-drive
```

The build validates the expected adapter assignment:

| pfSense interface | GNS3 adapter |
|---|---|
| WAN | `em0` |
| LAN | `em1` |
| OPT1 | `em2` |
| OPT2 | `em3` |

It then creates `artifacts/pfsense-config.img` and installs a mode-`600` copy at:

```text
~/GNS3/images/QEMU/pfsense-config.img
```

The generated image has an MBR partition table, a FAT16 partition labeled `PFSENSECFG`, and a configuration derived from the selected XML at `/config/config.xml`. FAT timestamps and the dummy administrator hash are fixed, so identical XML produces a byte-identical drive image.

While generating the drive, the administrator account in the copied configuration is deterministically replaced with the lab credential:

```text
Username: admin
Password: admin
```

The source XML is not modified. A private input receives the replacement bcrypt hash only in the ignored generated configuration media. The public input already contains the same deterministic dummy hash. This is a dummy lab password and must not be used on a production firewall.

Override paths when necessary:

```bash
make pfsense-config-drive \
  PFSENSE_CONFIG=/secure/path/config.xml \
  PFSENSE_CONFIG_IMAGE=/tmp/pfsense-config.img \
  GNS3_QEMU_IMAGES=/srv/gns3/images/QEMU
```

## Create the GNS3 template

```bash
make templates
```

This creates the `byot-cps - pfSense 2.8.1 Reproducible` template. Its disks are:

- HDA (`virtio`): `pfSense.qcow2`
- HDB (`ide`): `pfsense-config.img`
- CD-ROM: `netgate-installer-v1.2-RELEASE-amd64.iso`

## First installation

Create the topology and start `FIREWALL`:

```bash
PROJECT_NAME=byot-cps IOT_INTERFACE=docker0 make topology
```

In the pfSense installer:

1. Select **Configuration Restore**.
2. Select the `config.xml` found on the attached configuration media.
3. Install pfSense to HDA using the desired UFS or ZFS defaults.
4. Reboot from HDA.

The restored configuration should come up with WAN on `em0`, LAN on `em1`, OPT1 on `em2`, and OPT2 on `em3`. Log in with `admin` / `admin`.

The installation itself remains an interactive, one-time operation. For unattended CI, automate the installer in a separate image-build pipeline and publish the resulting configured qcow2 as a checksummed private artifact rather than committing it to Git.
