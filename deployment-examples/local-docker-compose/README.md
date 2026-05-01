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

Use these compose files:

- `compose.example.yaml`: baseline stack using published GHCR images.
- `compose.dev.yaml`: **recommended** local development workflow. Builds local service images and can optionally use a local `open-mpic-core-python` checkout.
- `compose.otel.yaml`: telemetry overlay (Prometheus/Grafana/Tempo/Loki/Collector). Combine with either base file above.

Baseline run (published images, no telemetry):

```sh
docker compose -f compose.example.yaml up -d
```

Recommended local dev run (single base file + telemetry overlay):

```sh
OPEN_MPIC_CORE_PATH=../../../open-mpic-core-python \
docker compose -f compose.dev.yaml -f compose.otel.yaml up -d --build
```

`compose.dev.yaml` works in both cases:

- With local core checkout present at `OPEN_MPIC_CORE_PATH`: container startup installs that local core checkout.
- Without local core checkout: startup falls back to the image-pinned core package and still runs.

This command starts the services and Traefik routes traffic through a single entrypoint.

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

## Deterministic Mixed CAA Traffic

To generate both successful and invalid MPIC CAA decisions with the split-DNS test setup, run:

```sh
./generate_mixed_caa_traffic.sh --iterations 10 --delay 0.2
```

This sends requests for two local-only domains:

- `valid.test.internal` returns the allowed CAA value from both checker DNS views and should produce `mpic_is_valid=True`.
- `invalid.test.internal` returns mismatched CAA values across the two checker DNS views and should produce `mpic_is_valid=False`.

If you update the zone files, restart the CoreDNS containers so they pick up the new records.

## Deterministic Controlled CAA/DCV Traffic

Use this script to generate deterministic valid and invalid traffic for both CAA and DCV checks:

```sh
./generate_controlled_traffic.sh --iterations 10 --delay 0.2
```

If you do not want to remember script names and flags, use the local Makefile instead:

```sh
make traffic
```

Useful Make targets:

```sh
make traffic
make traffic-mixed-caa
make traffic-caa-valid ITERATIONS=20 DELAY=0.1
make traffic-dcv-invalid ITERATIONS=20 DELAY=0.1
make traffic-random CHECK_TYPE=caa DOMAINS=good.test.internal
```

Useful filters:

```sh
# Only DCV invalid traffic
./generate_controlled_traffic.sh --check-type dcv --outcome invalid --iterations 20 --delay 0.1

# Only CAA valid traffic
./generate_controlled_traffic.sh --check-type caa --outcome valid --iterations 20 --delay 0.1
```

The script uses these deterministic local domains:

- `valid.test.internal` should pass CAA and DCV for both perspectives.
- `invalid.test.internal` should fail quorum for both CAA and DCV due to split-DNS mismatch.

## Stopping the Services

To stop all running services, use the following command:

```sh
docker compose down
```

This will stop and remove all the containers defined in the `compose.yml` file.

## Conclusion

You have successfully set up and run MPIC services with Docker Compose and Traefik.
