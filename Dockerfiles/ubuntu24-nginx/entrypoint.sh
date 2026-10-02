#!/bin/sh
set -eu
mkdir -p /run/sshd
ssh-keygen -A
/usr/sbin/sshd
/usr/sbin/nginx
echo "Ubuntu 24.04 GNS3 DMZ web server ready; HTTP: 80; SSH user: lab"
exec chroot --userspec=lab:lab --groups=sudo / sleep infinity
