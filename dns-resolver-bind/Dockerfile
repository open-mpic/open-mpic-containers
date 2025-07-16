FROM ubuntu:latest

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update packages and install BIND with required dependencies
RUN apt-get update && \
    apt-get install -y \
    bind9 \
    bind9-dnsutils \
    bind9-libs \
    bind9-utils \
    dnsutils \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Dist/package upgrade
RUN apt-get update && apt-get dist-upgrade -y

# Create the bind user (usually created by package, but ensuring it exists)
RUN useradd -r -s /usr/sbin/nologin -d /var/cache/bind -M bind || true

# Create directory structure required by BIND
RUN mkdir -p /etc/bind/zones /var/cache/bind /var/log/bind && \
    chown -R bind:bind /var/cache/bind /var/log/bind

# Copy the configuration file
COPY named.conf /etc/bind/named.conf

# Create missing zone files that named.conf references
RUN echo '$TTL 604800\n\
@       IN      SOA     localhost. root.localhost. (\n\
                        2022010101      ; Serial\n\
                        604800          ; Refresh\n\
                        86400           ; Retry\n\
                        2419200         ; Expire\n\
                        604800 )        ; Negative Cache TTL\n\
;\n\
@       IN      NS      localhost.\n\
@       IN      A       127.0.0.1\n\
@       IN      AAAA    ::1' > /etc/bind/db.local

RUN echo '$TTL 604800\n\
@       IN      SOA     localhost. root.localhost. (\n\
                        2022010101      ; Serial\n\
                        604800          ; Refresh\n\
                        86400           ; Retry\n\
                        2419200         ; Expire\n\
                        604800 )        ; Negative Cache TTL\n\
;\n\
@       IN      NS      localhost.\n\
1.0.0   IN      PTR     localhost.' > /etc/bind/db.127

RUN echo '$TTL 604800\n\
@       IN      SOA     localhost. root.localhost. (\n\
                        2022010101      ; Serial\n\
                        604800          ; Refresh\n\
                        86400           ; Retry\n\
                        2419200         ; Expire\n\
                        604800 )        ; Negative Cache TTL\n\
;\n\
@       IN      NS      localhost.' > /etc/bind/db.0

RUN echo '$TTL 604800\n\
@       IN      SOA     localhost. root.localhost. (\n\
                        2022010101      ; Serial\n\
                        604800          ; Refresh\n\
                        86400           ; Retry\n\
                        2419200         ; Expire\n\
                        604800 )        ; Negative Cache TTL\n\
;\n\
@       IN      NS      localhost.' > /etc/bind/db.255

# Set proper permissions
RUN chown -R bind:bind /etc/bind

# Create a simple startup script with debugging
RUN echo '#!/bin/sh\n\
    echo "Starting BIND DNS server..."\n\
    echo "Checking configuration..."\n\
    named-checkconf /etc/bind/named.conf\n\
    if [ $? -ne 0 ]; then\n\
        echo "Configuration check failed!"\n\
        exit 1\n\
    fi\n\
    echo "Configuration OK"\n\
    echo "Starting named..."\n\
    exec /usr/sbin/named -f -c /etc/bind/named.conf -u bind -g\n\
    ' > /start.sh && \
    chmod +x /start.sh

# Expose DNS ports
EXPOSE 53/tcp 53/udp

# Set healthcheck to verify BIND is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD dig @127.0.0.1 -p 53 localhost > /dev/null || exit 1

# Use startup script
CMD ["/start.sh"]