# Running MPIC Services with Docker Compose and Traefik

This guide will help you set up and run all MPIC services using Docker Compose and Traefik to route traffic to each service through a single port.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine

## Setup (Configuring the Services)

### config.yaml
Copy `compose.example.yaml` to `compose.yaml` to use the default config.

`compose.yaml` defines your Docker Compose configuration. It lists your MPIC services
(coordinator, CAA checkers, DCV checkers), other services (Traefik, Unbound), configures the network,
sets up the volumes for each service (for mounting service-specific configuration), and directly defines configuration
for each of the MPIC services.

### available_perspectives.yaml
Copy `resources/available_perspectives.example.yaml` to `resources/available_perspectives.yaml`, then modify it as
appropriate for your deployment.

This yaml file lists all the perspectives to which you are deploying your CAA and DCV checkers. It is consumed by
the coordinator service to determine which perspectives can be used for each check. It is also used by the
coordinator to determine whether a given set of corroborating perspectives is _valid_ by inspecting the RIR (Regional
Internet Registry) that is specified for each perspective.

Only use valid, real RIR codes (e.g., "ARIN") in this file.
If this file is improperly configured, the coordinator cannot reliably enforce a valid set of corroborating perspectives
and may return results that are not valid to allow issuance. Invalid RIR codes will result in a runtime error.

List of valid RIR codes:
- ARIN
- RIPE NCC
- APNIC
- LACNIC
- AFRINIC

The application in case-insensitive for RIR codes, but be sure to include the space if using "RIPE NCC".


Modify the yaml file to add or remove perspectives as needed.

It is recommended that the `available_perspectives.yaml` file be kept in sync with the perspectives configured in the
`compose.yaml` file (i.e., the perspectives to which you have deployed a checker).
You will not encounter errors if the yaml file defines extra perspectives to which you have not deployed a checker. 
You will, however, encounter errors if the yaml file does not define all the perspectives to which you _have_ deployed a checker.

Make sure the codes in the `available_perspectives.yaml` file correspond to the perspective codes used to specify CAA 
and DCV checker URLs in the `compose.yaml` file (as part of coordinator configuration).

### log_config.yaml
Copy `common_config/log_config.example.yaml` to `common_config/log_config.yaml`

This file defines the logging configuration for the services. You can customize the logging level and format as needed.

`TRACE` level is the lowest level of logging and will log everything including timing metrics. 
It is recommended to use `INFO` or `DEBUG` level for production deployments.

### uvicorn_config.yaml
Copy `common_config/uvicorn_config.example.yaml` to `common_config/uvicorn_config.yaml`

This file defines the Uvicorn configuration for the services. Uvicorn is the web server used to run the FastAPI 
applications that implement the MPIC services.

You can customize the host, port, server-side HTTP connection timeout, number of workers,
and other settings as needed.

## Running the Services

To start all services and Traefik, run the following command:

```sh
docker compose up -d
```

This command will start all the services defined in the `compose.yml` file and Traefik will route traffic to each service based on the defined rules.

## Accessing the Services

You can access your services using the following URLs:

- http://localhost:8000/dcv-checker-X/dcv - dcv service
- http://localhost:8000/caa-checker-X/caa - caa service
- http://localhost:8000/mpic-coordinator/mpic - coordinator service

You can also access the Traefik dashboard at [http://localhost:8080/dashboard](http://localhost:8080/dashboard).

## Example API Calls

Two simple API calls that can be run from the local machine while docker compose is running are:

(for a CAA query)

```
curl -H 'Content-Type: application/json'\
      -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' \
      -X POST \
      "http://localhost:8000/mpic-coordinator/mpic"
```

(for a DCV query)
```
curl -H 'Content-Type: application/json' \
      -d '{
  "check_type": "dcv",
  "domain_or_ip_target": "dns-01.integration-testing.open-mpic.org",
  "dcv_check_parameters": {
    "validation_method": "acme-dns-01",
    "key_authorization_hash": "7FwkJPsKf-TH54wu4eiIFA3nhzYaevsL7953ihy-tpo"
  }
}' \
      -X POST \
      "http://localhost:8000/mpic-coordinator/mpic"
```

Note: because this deployment is for testing, it does not implement the `x-api-key` header authentication.

## Stopping the Services

To stop all running services, use the following command:

```sh
docker compose down
```

This will stop and remove all the containers defined in the `compose.yml` file.

## Conclusion

You have successfully set up and run MPIC services with Docker Compose and Traefik.
