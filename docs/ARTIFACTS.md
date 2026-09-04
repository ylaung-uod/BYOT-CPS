# External artifacts

BYOT-CPS does not redistribute the Netgate Installer or vendor operating-system
images. The repository creates the blank pfSense installation disk locally and
installs only a vendor archive that matches the pinned manifest.

## Command summary

```bash
make fetch-help
make prepare-images
make verify-images
```

`fetch-help` prints the official acquisition and checksum URLs. It does not
download anything. `prepare-images` creates `pfSense.qcow2`, verifies the
compressed installer, decompresses it atomically, and verifies the resulting
ISO. `verify-images` checks the blank disk structurally and checks the ISO with
SHA-256.

Set `GNS3_QEMU_IMAGES=/path/to/GNS3/images/QEMU` for a non-default image
directory. Set `PFSENSE_INSTALLER_ARCHIVE=/path/to/file.iso.gz` when the
archive is not under `downloads/`.

## Netgate Installer acquisition

Netgate distributes the installer through its store. A Netgate Store account is
required; the installer is free, but the store checkout process is still used.
For this GNS3 virtual machine, select **AMD64 ISO IPMI/Virtual Machines**.[1]

The BYOT-CPS manifest is pinned to:

```text
Compressed:   netgate-installer-v1.2-RELEASE-amd64.iso.gz
SHA-256:      184514fe7df0d339362c1e33fa051c464577a450528759b343ade894c7c57955
Size:         342781760 bytes

Uncompressed: netgate-installer-v1.2-RELEASE-amd64.iso
SHA-256:      f55dc289eeda16c9698db092c93b3f26a36fdacaadc4fab67876530bd3aeae96
Size:         1059239936 bytes
```

The compressed checksum matches Netgate's current official checksum file.[4]
The uncompressed checksum and size were independently measured after
decompressing that exact archive; Netgate publishes checksums for the compressed
download, not the expanded ISO.[1] Do not rename or substitute a different
release to bypass the manifest. A future installer must be added deliberately
with both compressed and expanded hashes and a matching template filename.

Place the pinned archive at the default location:

```text
downloads/netgate-installer-v1.2-RELEASE-amd64.iso.gz
```

Then run:

```bash
make prepare-images
make verify-images
```

The archive and expanded ISO remain outside Git.

## Installer and pfSense version compatibility

The Netgate Installer is an online bootstrap environment: it downloads pfSense
installation packages rather than embedding them in the installer image.[2]
It therefore requires working WAN connectivity during installation. The version
selection normally offers the current pfSense release and one prior release,
but availability is determined by Netgate at installation time.[3]

The artifact preparation workflow is pinned to Netgate Installer 1.2. The
registered GNS3 template was read back with the 1.2 ISO attached, and the live
smoke test confirmed that the firewall VM and all containers start successfully.
The full firewall installation baseline was previously exercised with Netgate
Installer 1.1.1 and pfSense CE 2.8.1, including configuration restore,
installed-disk boot, HTTPS WebGUI response, and dummy administrator login. The
online version selection is controlled by Netgate rather than this
repository.[3]

For configuration restore, Netgate states that complete backups with a lower
configuration revision can be restored to a current release, which upgrades the
configuration format. A backup with a higher revision cannot be restored to an
older release, and partial backups require the same revision.[8] The tracked
`config/pfsense-public.xml` is a complete configuration tested on CE 2.8.1; do
not assume it can be restored to an older release.

## Blank installation disk

`pfSense.qcow2` is no longer an external prerequisite. `make prepare-images`
creates a new sparse 100 GiB qcow2 disk with:

```bash
qemu-img create -f qcow2 pfSense.qcow2 100G
```

QEMU documents `qemu-img create`, explicit formats, and `G` size suffixes for
this purpose.[5] Verification checks the qcow2 format and virtual size rather
than a byte hash because qcow2 metadata can differ between QEMU versions while
representing the same blank disk.

The generated disk is an installation target only. The source project's mutable
pfSense overlay is not copied into it.

## Licensing and redistribution boundary

Downloading, installing, or using Netgate software is subject to the terms
presented by Netgate, including its EULA and the license screen shown by the
installer.[3][6] The EULA restricts copying and reproduction except where its
terms or applicable open-source licenses allow it.[6] Netgate and pfSense marks
also remain subject to their trademark guidelines.[7]

For that reason this repository provides instructions, filenames, and checksums,
but does not automate the store checkout, publish a direct private download URL,
or redistribute installer media. Each operator must obtain the installer from
Netgate and review the terms that apply to their selected pfSense edition.

## Sources

[1] https://docs.netgate.com/pfsense/en/latest/install/download-installer-image.html — Download Installation Media | pfSense Documentation
[2] https://docs.netgate.com/pfsense/en/latest/install/netinstaller.html — Netgate Installer | pfSense Documentation
[3] https://docs.netgate.com/pfsense/en/latest/install/install-walkthrough.html — Installation Walkthrough | pfSense Documentation
[4] https://www.netgate.com/hubfs/pfSense-plus-installer-checksums.txt — Current Netgate Installer checksums
[5] https://www.qemu.org/docs/master/tools/qemu-img.html — QEMU disk image utility documentation
[6] https://www.netgate.com/company/legal/eula — Netgate End User License Agreement
[7] https://www.netgate.com/company/legal/trademarks — Netgate and pfSense trademark guidelines
[8] https://docs.netgate.com/pfsense/en/latest/backup/restore.html — Netgate backup compatibility guidance
