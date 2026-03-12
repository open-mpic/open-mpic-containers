# ===== BUILDER STAGE =====
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION} AS builder

# Arg for path to specific service to build
ARG SERVICE_PATH

RUN echo "building service from path: ${SERVICE_PATH}"

# Dist/package upgrade
RUN apt-get update && apt-get dist-upgrade -y

# Install Hatch
RUN pip install hatch

# Set the working directory
WORKDIR /app

# Copy just pyproject.toml first for better layer caching
COPY pyproject.toml .

# Copy the specific service code
COPY ${SERVICE_PATH} .

# Create production environment and install dependencies
RUN hatch env create production

# Install additional dependencies
RUN hatch env run -e production -- pip install PyYAML

# Upgrade pip packaging tools to latest to pick up any security fixes in
# pip/setuptools/wheel that may be bundled in the base Python image
RUN hatch env run -e production -- pip install --upgrade pip setuptools wheel

# ===== RUNTIME STAGE =====
FROM python:${PYTHON_VERSION}

# Upgrade OS packages and install runtime dependencies only
RUN apt-get update && apt-get dist-upgrade -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip setuptools wheel

# Note: System Python's pip/setuptools/wheel are upgraded to satisfy Trivy's vulnerability
# scanning, though the venv's versions (upgraded in the builder stage) take precedence at
# runtime via PATH=/venv/bin:$PATH. This ensures Trivy passes while keeping the active
# runtime clean.

# Set the working directory
WORKDIR /app

# Copy runtime dependencies and service files from builder
COPY --from=builder /venv /venv
COPY --from=builder /app /app

# Create config directory
RUN mkdir -p /app/config

# Copy configuration files and scripts
COPY uvicorn_config.yaml /app/config/
COPY run_uvicorn.py /app/
COPY docker-entrypoint.sh /app/

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Ensure venv is in PATH
ENV PATH="/venv/bin:$PATH"

# Set the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
