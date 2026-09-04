FROM ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98

ARG UBUNTU_SNAPSHOT=20260903T000000Z
ENV DEBIAN_FRONTEND=noninteractive
COPY isrg-root-x1.pem /etc/ssl/certs/ca-certificates.crt
RUN printf '%s\n' \
       "deb https://snapshot.ubuntu.com/ubuntu/${UBUNTU_SNAPSHOT} bionic main universe" \
       "deb https://snapshot.ubuntu.com/ubuntu/${UBUNTU_SNAPSHOT} bionic-updates main universe" \
       "deb https://snapshot.ubuntu.com/ubuntu/${UBUNTU_SNAPSHOT} bionic-security main universe" \
       > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl iproute2 iputils-ping net-tools \
       netcat-openbsd openssh-server procps sudo tcpdump \
    && rm -f /etc/ssh/ssh_host_* \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash lab \
    && usermod --password '$6$byotcps$ypK9Wt6JhQuEUL45vF7BrabMDI35pUOA6AHCVKV9fZfWxkItTYtR5W02Aq0Va9naZztO7YlIk6PcThgkEVUVH0' lab \
    && usermod -aG sudo lab \
    && mkdir -p /run/sshd \
    && printf 'PasswordAuthentication yes\nPermitRootLogin no\nUsePAM yes\n' > /tmp/byot-cps-sshd \
    && cat /etc/ssh/sshd_config >> /tmp/byot-cps-sshd \
    && mv /tmp/byot-cps-sshd /etc/ssh/sshd_config

COPY entrypoint.sh /usr/local/bin/lab-entrypoint
RUN chmod 0755 /usr/local/bin/lab-entrypoint
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/lab-entrypoint"]
