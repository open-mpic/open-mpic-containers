# (Example: For CAA Checker)
# docker build -t mpiccaachecker --build-arg SERVICE_PATH=src/mpic_caa_checker_service .

# Arg for Python version (with default)
ARG PYTHON_VERSION=3.11.9
FROM python:${PYTHON_VERSION}

# Arg for path to specific service to build
ARG SERVICE_PATH

RUN echo "building service from path: ${SERVICE_PATH}"

RUN python -m pip install hatch

# Set the working directory for subsequent instructions
WORKDIR ${SERVICE_PATH}

# Copy specific service code and common toml into the container
COPY ${SERVICE_PATH}/app ./app
COPY pyproject.toml .
RUN hatch dep show requirements > ./app/requirements.txt && python -m pip install --extra-index-url https://test.pypi.org/simple/ -r ./app/requirements.txt
EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]