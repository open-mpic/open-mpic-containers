# Unbound DNS Resolver Docker Image

A lightweight Docker container running Unbound DNS resolver based on Ubuntu.

## Building the Docker Image

```bash
# Build the Docker image
docker build -t unbound-dns .
```

## Running the Container

```bash
# Run the container in the background
docker run -d --name unbound-resolver -p 53:53/udp -p 53:53/tcp unbound-dns

# Check if the container is running
docker ps
```

## Testing the DNS Resolver

```bash
# Test basic DNS resolution
dig @127.0.0.1 google.com

# Check that DNSSEC is working
dig @127.0.0.1 +dnssec example.com

# View the logs
docker logs unbound-resolver

# Run a DNS lookup from inside the container
docker exec unbound-resolver dig @127.0.0.1 cloudflare.com
```

## Stopping and Cleaning Up

```bash
# Stop the container
docker stop unbound-resolver

# Remove the container
docker rm unbound-resolver

# Remove the image if needed
docker rmi unbound-dns
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

## Custom Configuration

To use a custom configuration file:

```bash
# Create a custom unbound.conf file
mkdir -p configs
# Edit your configuration in configs/unbound.conf

# Run with your custom configuration mounted
docker run -d --name unbound-resolver \
  -p 53:53/udp -p 53:53/tcp \
  -v $(pwd)/configs/unbound.conf:/etc/unbound/unbound.conf:ro \
  unbound-dns
```