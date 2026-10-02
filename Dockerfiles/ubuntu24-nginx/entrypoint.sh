#!/bin/sh
set -eu

install_gateway_dns() {
    echo "Waiting for default route before starting services"
    while :; do
        set -- $(ip -4 route get 1.1.1.1 2>/dev/null || true)
        while [ "$#" -gt 1 ]; do
            if [ "$1" = "via" ]; then
                gateway="$2"
                case "$gateway" in
                    ""|*[!0-9.]*) echo "Invalid IPv4 default gateway: $gateway" >&2; return 1 ;;
                esac
                if ! printf 'nameserver %s\noptions timeout:2 attempts:2\n' "$gateway" > /etc/resolv.conf; then
                    echo "Failed to install default-gateway DNS resolver" >&2
                    return 1
                fi
                echo "DNS resolver configured from default gateway: $gateway"
                return 0
            fi
            shift
        done
        sleep 1
    done
}

install_gateway_dns
mkdir -p /run/sshd
ssh-keygen -A
/usr/sbin/sshd
/usr/sbin/nginx
echo "Ubuntu 24.04 GNS3 DMZ web server ready; HTTP: 80; SSH user: lab"
exec chroot --userspec=lab:lab --groups=sudo / sleep infinity
