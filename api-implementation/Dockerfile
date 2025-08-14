# Start with any Python image that's not going to have memory leaks - it's just for bootstrapping Hatch
FROM python:3.13-alpine3.22

# Arg for path to specific service to build
ARG SERVICE_PATH

RUN echo "building service from path: ${SERVICE_PATH}"

# Dist/package upgrade (for python:3.13; doens't work for python:3.13-alpine)
# RUN apt-get update && apt-get dist-upgrade -y

# Dist/package upgrade (for python:3.13-alpine)
RUN apk update

# Alpine comes with sh instead of bash
RUN apk add --no-cache bash

# Install git (if building any dependencies from a git repository)
RUN apk add --no-cache git

# Install Hatch
RUN pip install hatch

# Set the working directory -- should create /src/mpic_{service_name}_service
WORKDIR /app

# Copy just pyproject.toml first for better layer caching
COPY pyproject.toml .

# Copy the specific service code
COPY ${SERVICE_PATH} .

# Create production environment and install dependencies
# This will install the Python version specified in pyproject.toml
RUN hatch env create production

# Install additional dependencies
RUN hatch env run -e production -- pip install PyYAML

# Create config directory
RUN mkdir -p /app/config

# Copy configuration files and scripts
COPY uvicorn_config.yaml /app/config/
COPY run_uvicorn.py /app/
COPY docker-entrypoint.sh /app/

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
