# Running MPIC Services with Docker Compose and Traefik

This guide will help you set up and run all MPIC services using Docker Compose and Traefik to route traffic to each service through a single port.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine

## Setup

Update the `configs` section in the `compose.yml` file with the correct values for your services.

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

## Stopping the Services

To stop all running services, use the following command:

```sh
docker compose down
```

This will stop and remove all the containers defined in the `compose.yml` file.

## Conclusion

You have successfully set up and run MPIC services with Docker Compose and Traefik.