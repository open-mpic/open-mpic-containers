# open-mpic-ec2-deployment
Deployment scripts for Open MPIC using Fast API, Docker, and Nginx


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

Assign the provided ips to the different subdomains using DNS. Wait for records to propagate before continuing to next step.


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