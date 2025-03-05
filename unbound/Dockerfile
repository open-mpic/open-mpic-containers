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

# Verify that nothing is running on port 53
RUN apt-get update && \
    apt-get install -y net-tools && \
    if netstat -tuln | grep -q ':53 '; then \
        echo "Warning: Something is already using port 53" && \
        netstat -tuln | grep ':53 '; \
    fi && \
    apt-get remove -y net-tools && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create directory structure required by the unbound.conf
RUN mkdir -p /opt/unbound/etc/unbound/var && \
    ln -s /etc/unbound /opt/unbound/etc/unbound || true

# Create _unbound user if it doesn't exist
RUN if ! id -u _unbound >/dev/null 2>&1; then \
        useradd -r -s /usr/sbin/nologin -d /var/lib/unbound -M _unbound; \
    fi

# Copy the configuration file
COPY unbound.conf /opt/unbound/etc/unbound/unbound.conf

# Find where unbound-anchor is installed
RUN which unbound-anchor || find / -name unbound-anchor -type f 2>/dev/null || echo "unbound-anchor not found"

# Set proper permissions
RUN chown -R _unbound:_unbound /opt/unbound /etc/unbound

# Disable chroot for container environment (it's redundant in Docker)
RUN sed -i 's|chroot: "/opt/unbound/etc/unbound"|chroot: ""|' /opt/unbound/etc/unbound/unbound.conf

# Expose DNS ports
EXPOSE 53/tcp 53/udp

# Set healthcheck to verify Unbound is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD dig @127.0.0.1 -p 53 localhost > /dev/null || exit 1

# Create a startup script
RUN echo '#!/bin/sh\n\
# Update DNSSEC root anchor if needed\n\
unbound-anchor -a "/opt/unbound/etc/unbound/var/root.key" || echo "Root anchor update failed, but continuing..."\n\
\n\
# Create directories if they do not exist\n\
mkdir -p /opt/unbound/etc/unbound/var\n\
chown -R _unbound:_unbound /opt/unbound/etc/unbound/var\n\
\n\
# Start Unbound in foreground mode\n\
exec /usr/sbin/unbound -d -c /opt/unbound/etc/unbound/unbound.conf\n\
' > /start.sh && \
chmod +x /start.sh

# Use startup script
CMD ["/start.sh"]