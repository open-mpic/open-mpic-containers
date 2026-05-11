# Running MPIC Services with Docker Compose and Traefik

This guide will help you set up and run all MPIC services using Docker Compose and Traefik to route traffic to each service through a single port.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine
- `make` (used for traffic generation scripts)

## Setup

1. Copy `resources/available_perspectives.example.yaml` to `resources/available_perspectives.yaml`
2. Copy `common_config/uvicorn_config.example.yaml` to `common_config/uvicorn_config.yaml`
3. Copy `common_config/log_config.example.yaml` to `common_config/log_config.yaml`

You can do all setup copies at once:

```sh
cp resources/available_perspectives.example.yaml resources/available_perspectives.yaml
cp common_config/uvicorn_config.example.yaml common_config/uvicorn_config.yaml
cp common_config/log_config.example.yaml common_config/log_config.yaml
```

## Running the Services

Use these compose files:

- `compose.example.yaml`: baseline stack using published GHCR images.
- `compose.dev.yaml`: **recommended** local development workflow. Builds local service images and defaults to the pinned `open-mpic-core` package from `pyproject.toml` (PyPI).
- `compose.otel.yaml`: telemetry overlay (Prometheus/Grafana/Tempo/Loki/Collector). Combine with either base file above.

## Telemetry Configuration (Environment Variables)

OpenTelemetry in the MPIC services is controlled by these environment variables:

- `OTEL_TRACES_ENABLED`
- `OTEL_METRICS_ENABLED`
- `OTEL_LOGS_ENABLED`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_SERVICE_NAME`
- `OTEL_RESOURCE_ATTRIBUTES`

When you include `compose.otel.yaml`, these are already set for Coordinator, CAA Checker, and DCV Checker containers.

Default values in this local stack:

- `OTEL_TRACES_ENABLED=true`
- `OTEL_METRICS_ENABLED=true`
- `OTEL_LOGS_ENABLED=true`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`
- `OTEL_SERVICE_NAME` set per service (for example `mpic-coordinator`)
- `OTEL_RESOURCE_ATTRIBUTES` includes `deployment.environment=local` (and perspective slot for checker instances)

If you do not include `compose.otel.yaml`, telemetry export is disabled by default.

Baseline run (published images, no telemetry):

```sh
docker compose -f compose.example.yaml up -d
```

Recommended local dev run (single base file + telemetry overlay):

```sh
docker compose -f compose.dev.yaml -f compose.otel.yaml up -d --build
```

`compose.dev.yaml` works in both cases:

- Default (no `LOCAL_CORE_PATH`): container startup uses the pinned core package from `pyproject.toml` (PyPI).
- With `LOCAL_CORE_PATH` set: container startup installs that local core checkout (editable install).

This command starts the services and Traefik routes traffic through a single entrypoint.

## Quickstart (Local Dev + Observability)

Bring up the full local stack (services + Grafana/Prometheus/Loki/Tempo):

```sh
docker compose -f compose.dev.yaml -f compose.otel.yaml up -d --build
```

To use a local core checkout instead of pinned PyPI:

```sh
LOCAL_CORE_PATH=../../../open-mpic-core-python \
docker compose -f compose.dev.yaml -f compose.otel.yaml up -d --build
```

Generate traffic so dashboards, logs, and traces populate:

```sh
make traffic
make traffic-mixed-caa
make traffic-dcv-invalid
```

Open Grafana at [http://localhost:3000](http://localhost:3000) (no login required — anonymous access is enabled), then:

1. Open dashboard `MPIC Overview` for metrics.
2. Open dashboard `MPIC Traces` for trace-focused triage.
3. Use the `Service Logs` panel for recent logs.
4. For traces, open Grafana `Explore`, choose data source `Tempo`, and run a TraceQL query like:

```traceql
{ resource.service.name =~ "mpic-.*" }
```

When you open a trace in Explore, Grafana shows span timing and a flamegraph-style span view.
You can also jump from Loki logs to Tempo traces via the `View Trace in Tempo` derived field when a log line contains a trace id.

### Note on span log icons in Tempo traces

When you click a log icon on a span, Grafana pivots to Loki using service labels and a span-adjacent time window.
Some spans may still show no logs if the application did not emit a log line during that exact span window.
This is expected and does not mean tracing is broken.

## Accessing the Services

You can access your services using the following URLs:

- <http://localhost:8000/dcv-checker-1/dcv> — DCV checker (instance 1)
- <http://localhost:8000/dcv-checker-2/dcv> — DCV checker (instance 2)
- <http://localhost:8000/caa-checker-1/caa> — CAA checker (instance 1)
- <http://localhost:8000/caa-checker-2/caa> — CAA checker (instance 2)
- <http://localhost:8000/mpic-coordinator/mpic> — coordinator (main entrypoint)

You can also access the Traefik dashboard at [http://localhost:8080/dashboard](http://localhost:8080/dashboard).

## Example API Calls

Two simple API calls that can be run from the local machine while docker compose is running are:

(for a CAA query)

```sh
curl -H 'Content-Type: application/json'\
      -d '{
  "check_type": "caa",
  "domain_or_ip_target": "example.com"
}' \
      -X POST \
      "http://localhost:8000/mpic-coordinator/mpic"
```

(for a DCV query)

```sh
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
