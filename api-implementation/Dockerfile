# --- Builder stage ---
# Use Python 3.11 so compiled extension wheels are compatible with the distroless final image (python3)
FROM python:3.11-slim AS builder

# Arg for path to specific service to build
ARG SERVICE_PATH

WORKDIR /app

# Copy just pyproject.toml first for better layer caching
COPY pyproject.toml .

# Copy the specific service code into the project root so pyproject.toml applies
COPY ${SERVICE_PATH} .

# Install pip and build the project into a deps directory (no venv)
RUN pip install --upgrade pip

# Install the service and runtime dependencies into /app/deps
# This avoids copying a full virtualenv into the final image and
# keeps Python runtime files isolated under /app/deps
RUN pip install --no-cache-dir --target=/app/deps /app

# Copy config and scripts
WORKDIR /app
RUN mkdir -p /app/config
COPY uvicorn_config.yaml /app/config/
COPY run_uvicorn.py /app/

# --- Final stage: distroless ---
FROM gcr.io/distroless/python3-debian12
WORKDIR /app


# Copy application and deps from builder
COPY --from=builder /app /app

# Use the installed deps directory as PYTHONPATH (no venv)
ENV PYTHONPATH=/app/deps
ENV PYTHONUNBUFFERED=1

# Expose port 80 for HTTP
EXPOSE 80
# Run with the distroless python3 executable
ENTRYPOINT ["python3", "/app/run_uvicorn.py"]
