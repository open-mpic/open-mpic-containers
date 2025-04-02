# open-mpic-containers
Implements a FastAPI wrapper for Open MPIC using Docker.
Built on [open-mpic-core-python](https://github.com/open-mpic/open-mpic-core-python).

Includes various deployment configurations, including:
 - AWS EC2
 - Local Docker Compose
 - Local Kubernetes

# Architecture

Open MPIC Containers implements a REST API interface to implement the Open MPIC API and uses REST API calls to communicate with remote perspectives.
The repository contains three containers:
- Coordinator: Terminates Open MPIC API calls per the Open MPIC API spec, selects remote perspectives from a list of available perspectives, and sends REST API calls to those perspectives.
- DCV Checker: Terminates REST API calls for DCV checks and performs the checks. This container implements a single remote DCV perspective.
- CAA Checker: Terminates REST API calls for CAA checks and performs the checks. This container implements a single remote CAA perspective.

Different deployments (see deployment examples) will wrap deploy these containers indifferent contexts (e.g., docker compose, kubernetes) and may use various network architectures (e.g., public Internet, VPN, service mesh network) to facilitate calls between the containers. The containers may be placed beyond ingress and load balancing to provide optimal uptime and scaling. This is recommended for a production deployment.

## Authentication

The containers themselves **do not contain any authentication or terminate TLS**. The appropriate security model of these systems is left to the deploying CAs. To comply with the MPIC requirement of the CA/Browser Forum Baseline Requirements, **any production deployment must properly implement security**. Some example approaches are:

- Transport encryption: Ensure containers are protected from any direct communication from the outside Internet and place containers behind a TLS-terminating reverse proxy (e.g., Nginx).
- Caller authentication: Ensure presence of a secret authentication header (e.g., `x-api-key: ` or `Authorization: Bearer` header) on all client calls coming from the outside Internet.

These particular techniques are utilized in the AWS EC2 deployment example.

# Images

Images are auto built using a GitHub action. These are pushed to the GitHub Container Registry and may be used to pull in images in K8s, docker compose, etc... Instructions for manually building images are contained in `api-implementation/README.md`

# Appendix: Devcontainers
This repository contains a `.devcontainer` folder containing a `devcontainer.json` that can be used to develop open-mpic services. 

Refer to the [Visual Studio Code Remote - Containers](https://code.visualstudio.com/docs/remote/containers) documentation for more information on how to use devcontainers.

Once you have opened the repository in a devcontainer, and it builds for the first time, close the terminal and reopen it to ensure that the environment is set up correctly and tools such as `pyenv` are available in the PATH.

Once your environment is set up, change to the directory of the service you want to work on and run the following commands:

```bash
# Change to the directory of the service you want to work on
cd mpic_coordinator_service
# Install the python version specified in the .python-version file
pyenv install
# Activate the python version specified in the .python-version file
pyenv activate
# Install the dependencies
pip install -r requirements.txt
# Start the service
fastapi dev
```
