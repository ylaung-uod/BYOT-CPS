# VM image inputs

Run the artifact workflow instead of copying files from another GNS3 host:

```bash
make fetch-help
make prepare-images
make verify-images
```

`make prepare-images` creates a fresh sparse 100 GiB `pfSense.qcow2` locally.
It verifies and expands the operator-supplied
`netgate-installer-v1.2-RELEASE-amd64.iso.gz` into the GNS3 QEMU image
directory. The vendor archive is not downloaded or redistributed by this
repository.

`images.json` is authoritative for filenames, sizes, SHA-256 values, and blank
disk properties. Legacy source-project MD5 values are retained only as
historical GNS3 Marketplace metadata and are not used for verification.

See [`../docs/ARTIFACTS.md`](../docs/ARTIFACTS.md) for the official Netgate
checkout flow, exact compressed and expanded checksums, version compatibility,
and licensing boundary.
