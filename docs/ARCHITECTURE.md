# byot-cps architecture

## System model

BYOT-CPS is a declarative builder for a GNS3 cyber-physical security lab. It
separates four layers:

1. `topology.json` declares nodes, coordinates, adapters, ports, and links.
2. `gns3_templates.json` declares semantic QEMU and Docker templates without
   server-local UUIDs.
3. `images.json`, `container_images.json`, and the tracked SBOMs identify base
   artifacts and package inputs.
4. `config/pfsense-public.xml` and `src/pfsense_config.py` provide the synthetic
   firewall state restored during installation.

GNS3 allocates project and template UUIDs at runtime. The build discovers those
UUIDs by semantic name, reconciles the complete managed payload, and reads each
template back after creation or update.

## Default topology

The default project has 16 nodes and 15 links:

```text
                                      +-- MGMT-ADMIN
                                      |
ISP -- WAN-SWITCH -- FIREWALL -- MGMT-SWITCH
         |                |
         |                +-- DMZ-SWITCH -- DMZ-WEB-SERVER
         |
         +-- EXTERNAL-CLIENT
         +-- C2-SIMULATOR

FIREWALL -- CPS-SWITCH -- CPS-OPERATOR
                      |-- IoT (host interface)
                      |-- RED-TEAM-HOST
                      `-- COMPROMISED-IOT-01..N
```

`FIREWALL` is a pfSense QEMU node. `ISP` is the GNS3 NAT node. The four switches
are GNS3 Ethernet switches. All Ubuntu roles are lightweight Docker nodes; role
names do not imply that bot, C2, exploit, or malware software is present.

## Interface and segment model

| Segment | pfSense adapter | Firewall address | Switch | Attached roles |
|---|---:|---|---|---|
| WAN | `em0` / adapter 0 | DHCP | `WAN-SWITCH` | `ISP`, `EXTERNAL-CLIENT`, `C2-SIMULATOR` |
| Management | `em1` / adapter 1 | `192.168.99.1/24` | `MGMT-SWITCH` | `MGMT-ADMIN` |
| DMZ | `em2` / adapter 2 | `172.20.0.1/24` | `DMZ-SWITCH` | `DMZ-WEB-SERVER` |
| CPS | `em3` / adapter 3 | `10.0.0.1/24` | `CPS-SWITCH` | `CPS-OPERATOR`, `IoT`, `RED-TEAM-HOST`, compromised-IoT pool |

The public firewall configuration enables DHCP pools `.5` through `.100` on
the three internal segments. Container addresses are not configured
persistently; the clean-clone procedure in [`../QUICKSTART.md`](../QUICKSTART.md)
shows temporary examples outside those pools.

## Exact default links

| Endpoint A | Endpoint B |
|---|---|
| `ISP` port 0 | `WAN-SWITCH` port 0 |
| `WAN-SWITCH` port 1 | `FIREWALL` adapter 0 (`em0`) |
| `FIREWALL` adapter 1 (`em1`) | `MGMT-SWITCH` port 0 |
| `FIREWALL` adapter 2 (`em2`) | `DMZ-SWITCH` port 0 |
| `FIREWALL` adapter 3 (`em3`) | `CPS-SWITCH` port 0 |
| `MGMT-ADMIN` adapter 0 | `MGMT-SWITCH` port 1 |
| `CPS-OPERATOR` adapter 0 | `CPS-SWITCH` port 1 |
| `EXTERNAL-CLIENT` adapter 0 | `WAN-SWITCH` port 2 |
| `IoT` port 0 | `CPS-SWITCH` port 2 |
| `DMZ-WEB-SERVER` adapter 0 | `DMZ-SWITCH` port 1 |
| `COMPROMISED-IOT-01..N` adapter 0 | `CPS-SWITCH` ports 3 through `N+2` |
| `C2-SIMULATOR` adapter 0 | `WAN-SWITCH` port 3 |
| `RED-TEAM-HOST` adapter 0 | `CPS-SWITCH` port `N+3` |

For `N` compromised-IoT containers, the generated project contains `13 + N`
nodes and `12 + N` links. `N=0` is valid. Node names and switch-port assignment
remain deterministic.

## Host-interface boundary

The `IoT` cloud node resolves `${IOT_INTERFACE}` when the project is built. The
default is `docker0`, which is suitable for a host-only demonstration on many
Linux systems. A physical interface may be selected explicitly, but doing so
bridges host traffic into the experimental CPS segment. Never select a
production, management, or Internet-facing interface without reviewing the
firewall policy and accepting that exposure.

## Build flow

```text
manifests + Dockerfiles + public config
                  |
                  v
      validate and prepare artifacts
                  |
                  v
      reconcile semantic templates
                  |
                  v
      create project nodes and links
                  |
                  v
      read back, start, verify, delete smoke project
```

The topology builder refuses to modify an existing project with the requested
name. A partial project created during a failed build is deleted. See
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for represented and unrepresented
state and [`SECURITY-BOUNDARY.md`](SECURITY-BOUNDARY.md) for operating limits.
