#!/bin/sh
set -eu
mkdir -p /run/sshd
ssh-keygen -A
/usr/sbin/sshd
echo "Ubuntu 18.04 GNS3 lab container ready; SSH user: lab"
exec chroot --userspec=lab:lab --groups=sudo / sleep infinity
