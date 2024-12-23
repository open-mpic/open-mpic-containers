# Start with any Python image - it's just for bootstrapping Hatch
FROM python:3.13

# Arg for path to specific service to build
ARG SERVICE_PATH

RUN echo "building service from path: ${SERVICE_PATH}"

# Install Hatch
RUN pip install hatch

# Set the working directory -- should create /src/mpic_{service_name}_service
WORKDIR /${SERVICE_PATH}

# Copy just pyproject.toml first for better layer caching
COPY pyproject.toml .

# Copy the specific service code
COPY ${SERVICE_PATH}/app ./app

# Create production environment and install dependencies
# This will install the Python version specified in pyproject.toml
RUN hatch env create production

# Run the service using uvicorn with the production environment
CMD ["hatch", "env", "run", "-e", "production", "--", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]