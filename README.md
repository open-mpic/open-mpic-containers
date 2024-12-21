# open-mpic-restapi-server
Implements a FastAPI wrapper for Open MPIC using Docker.
Built on [open-mpic-core-python](https://github.com/open-mpic/open-mpic-core-python).

Includes various deployment configurations, including:
 - AWS EC2
 - (tbd)

## Development
Instructions for developing and deploying the Open MPIC REST services.

#### Appendix: Devcontainers
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

# Config
`cp config.example.yaml config.yaml`


Pick a domain name suffix at the prompt that you control which you can use to allocate subdomains to perspectives.
`./configure.py`

# Tofu apply
`cd open-tofu`

`tofu apply -auto-approve`

`cd ..`

# Update domain names


`./get_ips.py`

Assign the provided ips to the different subdomains using DNS. Wait for records to propagate before continuing to the next step.


# Install

`./install.py`

# Run Open MPIC

All perspectives host a /mpic endpoint and run a coordinator. Use ./get_ips.py -s mpic.example.com to get a list of domains that can be used as the hostname for open mpic calls.

example:

``
time curl -H 'Content-Type: application/json' \
      -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' \
      -X POST \
      "https://1-2-3-4.mpic.example.com/mpic"
``

# Teardown
If you are done using the MPIC service:

`cd open-tofu`

`tofu destroy -auto-approve`