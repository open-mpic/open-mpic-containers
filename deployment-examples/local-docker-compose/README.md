# Running MPIC Services with Docker Compose and Traefik

This guide will help you set up and run all MPIC services using Docker Compose and Traefik to route traffic to each service through a single port.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine

## Setup

1. Copy `config.example.yaml` to `config.yaml` to use the default config.
2. Copy `resources/available_perspectives.example.yaml` to `resources/available_perspectives.yaml`

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

  "validation_details": {
    "validation_method": "acme-dns-01",
    "key_authorization": "7FwkJPsKf-TH54wu4eiIFA3nhzYaevsL7953ihy-tpo"
    }
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
