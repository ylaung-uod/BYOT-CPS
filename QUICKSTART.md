# byot-cps quick-start manual

This guide takes a clean host from repository checkout to a running `byot-cps` topology in GNS3.

## 1. Understand what will be created

The default topology contains:

- 1 pfSense QEMU firewall
- 9 Ubuntu Docker containers
- 4 Ethernet switches
- 1 NAT node
- 1 host-interface cloud node
- 16 nodes and 15 links in total

The compromised-IoT pool defaults to three containers. For a pool of `N` containers, the generated topology contains `13 + N` nodes and `12 + N` links.

## 2. Check the host prerequisites

The template was developed with GNS3 2.2.55 on Linux. Verify the required commands:

```bash
gns3server --version
docker --version
qemu-system-x86_64 --version
python3 --version
make --version
command -v sfdisk mkfs.vfat mcopy mmd
```

Docker must work without `sudo`:

```bash
docker run --rm hello-world
```

KVM should be available:

```bash
test -e /dev/kvm && echo "KVM available"
```

On Ubuntu, the non-GNS3 dependencies can typically be installed with:

```bash
sudo apt update
sudo apt install -y make docker.io qemu-system-x86 qemu-utils dosfstools mtools fdisk python3
```

Install and start GNS3 separately if it is not already present. The scripts read the local server address and credentials from:

```text
~/.config/GNS3/2.2/gns3_server.conf
```

If yours is elsewhere, pass it explicitly to GNS3-dependent targets:

```bash
make templates GNS3_SERVER_CONFIG=/path/to/gns3_server.conf
```

## 3. Enter the source tree

```bash
git clone <repository-url> byot-cps
cd byot-cps
```

Alternatively, extract the minimal reproduction archive from the GitHub
release and enter its `byot-cps-v1.0.0` directory. Verify its contents before
continuing:

```bash
sha256sum -c REPRODUCTION-MANIFEST.sha256
```

For a Git checkout, confirm that the working tree is clean:

```bash
git status --short --branch
```

## 4. Acquire and prepare the pfSense artifacts

Print the authoritative Netgate download and checksum locations:

```bash
make fetch-help
```

Using a Netgate Store account, complete the free checkout for the AMD64 ISO
installer. Save the pinned archive as:

```text
downloads/netgate-installer-v1.2-RELEASE-amd64.iso.gz
```

Create a new blank 100 GiB `pfSense.qcow2`, verify the compressed archive,
decompress it into the GNS3 image directory, and verify the expanded ISO:

```bash
make prepare-images
make verify-images
```

The expected verification result is two `OK` lines. The repository never
downloads or redistributes the vendor installer. See
[`docs/ARTIFACTS.md`](docs/ARTIFACTS.md) for exact filenames, compressed and
expanded SHA-256 values, version compatibility, and licensing notes.

For non-default locations, use:

```bash
make prepare-images \
  PFSENSE_INSTALLER_ARCHIVE=/path/to/netgate-installer-v1.2-RELEASE-amd64.iso.gz \
  GNS3_QEMU_IMAGES=/path/to/GNS3/images/QEMU
make verify-images GNS3_QEMU_IMAGES=/path/to/GNS3/images/QEMU
```

## 5. Select the pfSense configuration

The default build uses the tracked synthetic configuration:

```text
config/pfsense-public.xml
```

It contains only documented lab addresses, basic outbound rules, and the dummy
`admin` / `admin` credential. Validate it with:

```bash
make pfsense-config-validate
```

The expected mapping is:

| Segment | pfSense interface | Address |
|---|---|---|
| WAN | `em0` | DHCP |
| Management | `em1` | `192.168.99.1/24` |
| DMZ | `em2` | `172.20.0.1/24` |
| CPS | `em3` | `10.0.0.1/24` |

For a private deployment, provide an external backup explicitly:

```bash
install -m 600 /secure/path/config.xml secrets/pfsense/config.xml
PFSENSE_CONFIG=secrets/pfsense/config.xml make pfsense-config-validate
```

The complete `secrets/` directory is excluded from Git. During
configuration-drive generation, only the generated copy receives the dummy
`admin` password; the private source XML is not modified.

## 6. Build images and create GNS3 templates

Start the GNS3 application or local GNS3 server first. Then run:

```bash
make templates
```

If GNS3 uses a different QEMU executable, specify it during template creation:

```bash
make templates QEMU_PATH=/path/to/qemu-system-x86_64
```

This command performs the complete prerequisite chain:

1. Validates the topology.
2. Prepares and verifies the pfSense installer and blank disk.
3. Builds the pinned Ubuntu 18.04 and 24.04 Docker images.
4. Validates the selected public or private pfSense XML.
5. Builds and installs `pfsense-config.img`.
6. Creates missing GNS3 node templates and reconciles stale owned templates.

Confirm these templates under **Edit → Preferences** in GNS3:

```text
byot-cps - pfSense 2.8.1 Reproducible
byot-cps - Ubuntu 18.04 Lab Container
byot-cps - Ubuntu 24.04 Lab Container
```

Template reconciliation is idempotent: matching templates are left unchanged,
and stale same-name BYOT-CPS templates are updated to the declared payload.

## 7. Run the automated smoke test

```bash
make smoke-test
```

The smoke test creates a temporary topology, checks its nodes and links, confirms the pfSense configuration drive, starts the firewall and all containers, and deletes the temporary project.

Test a different compromised-IoT count with:

```bash
make smoke-test COMPROMISED_IOT_COUNT=5
```

## 8. Choose the IoT host interface

The `IoT` cloud node connects a host interface directly to `CPS-SWITCH`. List available interfaces:

```bash
ip -brief link
```

For a host-only demonstration, use `docker0`. To connect a physical test device, use its actual Ethernet interface instead.

Do not attach an interface carrying production or untrusted traffic to an experimental topology.

## 9. Create the persistent GNS3 project

If no project named `byot-cps` exists:

```bash
IOT_INTERFACE=docker0 \
COMPROMISED_IOT_COUNT=3 \
make topology
```

The default project name is `byot-cps`. The builder refuses to overwrite an existing project. If that name already exists, either remove it through GNS3 after confirming it is no longer needed, or create a new project name:

```bash
PROJECT_NAME=byot-cps-demo \
IOT_INTERFACE=docker0 \
COMPROMISED_IOT_COUNT=3 \
make topology
```

For ten compromised-IoT nodes:

```bash
PROJECT_NAME=byot-cps-10 \
IOT_INTERFACE=docker0 \
COMPROMISED_IOT_COUNT=10 \
make topology
```

## 10. Open the topology in GNS3

Open the generated project and confirm the network roles:

```text
ISP -- WAN-SWITCH -- FIREWALL
       |            |-- MGMT-SWITCH -- MGMT-ADMIN
       |            |-- DMZ-SWITCH  -- DMZ-WEB-SERVER
       |            `-- CPS-SWITCH  -- CPS-OPERATOR, IoT,
       |                                RED-TEAM-HOST,
       |                                COMPROMISED-IOT-NN
       |-- C2-SIMULATOR
       `-- EXTERNAL-CLIENT
```

## 11. Install and restore pfSense

Start `FIREWALL` first and open its VNC console. The VM has:

- HDA: blank `pfSense.qcow2`
- HDB: generated `pfsense-config.img`
- CD-ROM: Netgate installer ISO

In the installer:

1. Select **Configuration Restore**.
2. Select `config.xml` from the attached `PFSENSECFG` media.
3. Install pfSense to HDA using the desired UFS or ZFS defaults.
4. Reboot from HDA.
5. If the installer starts again, eject the ISO or change the VM boot priority to HDA.

After restoration, use:

```text
Username: admin
Password: admin
```

Confirm the interfaces:

```text
WAN  = em0 = DHCP
LAN  = em1 = 192.168.99.1/24
OPT1 = em2 = 172.20.0.1/24
OPT2 = em3 = 10.0.0.1/24
```

The configuration enables DHCP pools on the internal segments:

| Segment | DHCP range |
|---|---|
| Management | `192.168.99.5`–`192.168.99.100` |
| DMZ | `172.20.0.5`–`172.20.0.100` |
| CPS | `10.0.0.5`–`10.0.0.100` |

## 12. Start the Docker containers

Select the required containers and click **Start**. Their common credentials are:

```text
Username: lab
Password: lab
```

The `lab` account has password-protected sudo access. Root SSH login is disabled.

The images do not automatically assign addresses. Use a GNS3 console to set a temporary address. For example, on `MGMT-ADMIN`:

```bash
sudo ip address add 192.168.99.201/24 dev eth0
sudo ip link set eth0 up
sudo ip route replace default via 192.168.99.1
```

On `DMZ-WEB-SERVER`:

```bash
sudo ip address add 172.20.0.201/24 dev eth0
sudo ip link set eth0 up
sudo ip route replace default via 172.20.0.1
```

On a CPS container, choose a unique address outside the configured DHCP pool, for example:

```bash
sudo ip address add 10.0.0.201/24 dev eth0
sudo ip link set eth0 up
sudo ip route replace default via 10.0.0.1
```

These `ip` commands are temporary and must be repeated after recreating or restarting a container unless startup configuration is added to its image.

## 13. Test connectivity

From each internal segment, test its pfSense gateway:

```bash
ping -c 3 192.168.99.1  # Management
ping -c 3 172.20.0.1    # DMZ
ping -c 3 10.0.0.1    # CPS
```

After assigning an address, test SSH from a reachable peer:

```bash
ssh lab@<container-ip>
```

The first connection will prompt for the container's newly generated host key.

## 14. Useful rebuild commands

Rebuild only the Docker images:

```bash
make docker-images
```

Rebuild only the pfSense configuration drive:

```bash
make pfsense-config-drive
```

The following specification refresh and unit-test commands are maintainer-only
and available in the full source repository, not the minimal archive.
Regenerate the portable topology from the original source project:

```bash
make refresh-spec SOURCE_PROJECT=/path/to/project/project.gns3
make validate
```

The private source project is not included in this repository, so
`SOURCE_PROJECT` is required when refreshing the exported specification.

Run all Python tests:

```bash
make test
```

## Troubleshooting

### GNS3 server connection fails

Start GNS3 and verify:

```bash
curl -u '<gns3-user>:<gns3-password>' http://127.0.0.1:3080/v2/version
```

Do not put real GNS3 credentials in the repository.

### A required image is missing

Run:

```bash
make verify-images
```

Place the reported file in `~/GNS3/images/QEMU` and retry.

### The project already exists

The builder intentionally refuses to modify it. Use a unique `PROJECT_NAME` or remove the old project through GNS3 after confirming it is disposable.

### The IoT cloud node fails

Check that the selected interface exists:

```bash
ip link show <interface-name>
```

Then regenerate with the correct `IOT_INTERFACE`.

### SSH is refused

Check that the container is running, has an address, and that TCP port 22 is listening:

```bash
ip address show eth0
ss -lnt | grep ':22'
```

### Container host-key warning after recreation

Each new container generates a new SSH host key. Remove only the obsolete entry for the test address:

```bash
ssh-keygen -R <container-ip>
```

## Security boundary

This is an experimental topology with dummy credentials. Keep it isolated from production networks. The images contain no operational bot or C2 software. The tracked public pfSense XML contains synthetic lab data only. Generated configuration drives and any operator-supplied private XML remain excluded from Git.
