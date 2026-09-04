# Reproducible lab containers

BYOT-CPS builds two benign diagnostic container images:

- `byot-cps/ubuntu18-lab:latest`
- `byot-cps/ubuntu24-lab:latest`

Their build and runtime expectations are declared in `container_images.json`.

## Pinned package inputs

Both Ubuntu base images are pinned by OCI digest. Package installation uses the
Ubuntu archive snapshot `20260903T000000Z`, so the package indexes and package
versions do not drift with the live Ubuntu mirrors. Ubuntu documents snapshot
IDs in `YYYYMMDDTHHMMSSZ` form and describes snapshots as views of the archive
at a specified date and time.[1]

The minimal Ubuntu base layers do not initially contain a CA certificate bundle.
Each build context therefore carries the self-signed ISRG Root X1 certificate
published by Let's Encrypt, pinned in `container_images.json` by SHA-256.[3] It
bootstraps authenticated HTTPS access to `snapshot.ubuntu.com`; the normal
`ca-certificates` package replaces it during installation. APT also verifies
Ubuntu-signed repository metadata and the package checksums chained from it.[2]

The snapshot service currently promises snapshots for at least two years and
may retain them longer.[1] A future release should advance the snapshot only as
an explicit, reviewed dependency update and regenerate both SBOMs.

## Build and package records

```bash
make docker-images
make container-sboms
make container-sboms-check
```

`src/generate_container_sboms.py` queries every installed Debian package and
writes deterministic SPDX 2.3 JSON documents:

- `sbom/ubuntu18-lab.spdx.json`
- `sbom/ubuntu24-lab.spdx.json`

The SBOMs record exact package names, versions, architectures, base-image
digests, and the Ubuntu snapshot. `container-sboms-check` regenerates the
expected documents in memory and fails if either tracked SBOM is stale.

## Runtime verification

```bash
make container-runtime-test
```

For each image, `src/test_container_images.py` starts a temporary container and
checks:

- the expected Ubuntu `VERSION_ID`;
- the long-running PID 1 workload uses the `lab` user;
- `lab` belongs to the `sudo` group;
- non-interactive sudo without a password fails;
- the documented `lab` password enables sudo;
- SSH enables password authentication, disables root login, and uses PAM;
- all required network and diagnostic tools exist;
- only TCP port 22 listens;
- only the declared `sleep` workload and `sshd` service remain running; and
- executable directories contain no names matching the declared malware/miner
  markers.

The service/process/listener allowlists detect unexpected services and common
operational-malware indicators. They are a bounded runtime policy check, not a
claim that filename checks can prove the absence of all malicious code. The
images intentionally contain no bot, C2, scanner, exploit, or mining payload.

Run the complete Phase 4 container gate with:

```bash
make phase4-verify
```

## Related reproducibility gates

GNS3 template reconciliation compares declared payload fields, updates stale
same-name BYOT-CPS templates, and reads each template back after creation or
update. The public pfSense-drive test builds the image twice, compares SHA-256,
extracts `config.xml`, and compares canonical XML with the tracked public
configuration.

## Sources

[1] https://snapshot.ubuntu.com/ — Ubuntu Snapshot Service
[2] https://manpages.ubuntu.com/manpages/noble/en/man8/apt-secure.8.html — apt-secure: archive authentication support for APT
[3] https://letsencrypt.org/certificates/ — Let's Encrypt Chains of Trust
