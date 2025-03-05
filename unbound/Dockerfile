FROM ubuntu:latest

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update packages and install Unbound with required dependencies
RUN apt-get update && \
    apt-get install -y \
    unbound \
    unbound-anchor \
    dnsutils \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create the _unbound user
RUN useradd -r -s /usr/sbin/nologin -d /var/lib/unbound -M _unbound

# Create directory structure required by the unbound.conf
RUN mkdir -p /opt/unbound/etc/unbound/var && \
    ln -s /etc/unbound /opt/unbound/etc/unbound || true

# Copy the configuration file
COPY unbound.conf /opt/unbound/etc/unbound/unbound.conf

# Set proper permissions
RUN chown -R _unbound:_unbound /opt/unbound /etc/unbound

# Disable chroot for container environment (it's redundant in Docker)
RUN sed -i 's|chroot: "/opt/unbound/etc/unbound"|chroot: ""|' /opt/unbound/etc/unbound/unbound.conf

# Create a simple startup script
RUN echo '#!/bin/sh\n\
# Update DNSSEC root anchor if needed\n\
unbound-anchor -a "/opt/unbound/etc/unbound/var/root.key" || echo "Root anchor update failed, continuing anyway"\n\
# Create/ensure var directory exists\n\
mkdir -p /opt/unbound/etc/unbound/var\n\
chown -R _unbound:_unbound /opt/unbound/etc/unbound/var\n\
# Start Unbound in foreground mode\n\
exec /usr/sbin/unbound -d -c /opt/unbound/etc/unbound/unbound.conf\n\
' > /start.sh && \
chmod +x /start.sh

# Expose DNS ports
EXPOSE 53/tcp 53/udp

# Set healthcheck to verify Unbound is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD dig @127.0.0.1 -p 53 localhost > /dev/null || exit 1

# Use startup script
CMD ["/start.sh"]