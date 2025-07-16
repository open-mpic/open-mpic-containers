# BIND DNS Resolver Docker Image

A lightweight Docker container running BIND DNS resolver based on Ubuntu.

The provided config is an example only. Please consider the DNS needs of your deployment and appropriately tune Unbound.

## Building the Docker Image

```bash
# Build the Docker image
docker build -t bind-dns .
```

## Running the Container

```bash
# Run the container in the background
docker run -d --name bind-resolver -p 53:53/udp -p 53:53/tcp bind-dns

# Check if the container is running
docker ps
```

## Testing the DNS Resolver

```bash
# Test basic DNS resolution
dig @127.0.0.1 google.com

# Test DNSSEC validation
dig @127.0.0.1 +dnssec example.com

# Force TCP protocol
dig @127.0.0.1 +tcp cloudflare.com

# Reverse DNS lookup
dig @127.0.0.1 -x 8.8.8.8

# Test from inside the container
docker exec bind-resolver dig @127.0.0.1 github.com
```

## Customizing BIND Configuration

```bash
# Create a custom named.conf file
mkdir -p configs
# Edit your configuration in configs/named.conf
# Run with your custom configuration mounted
docker run -d --name bind-resolver \
  -p 53:53/udp -p 53:53/tcp \
  -v $(pwd)/configs/named.conf:/etc/bind/named.conf:ro \
  bind-dns
```

## Stopping and Cleaning Up

```bash
# Stop the container
docker stop bind-resolver

# Remove the container
docker rm bind-resolver
```

## Troubleshooting

If you encounter issues with port 53 being already in use on your host:

```bash
# Check what's using port 53 on your host
sudo lsof -i :53

# On many Linux systems, you may need to disable systemd-resolved
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved
```


