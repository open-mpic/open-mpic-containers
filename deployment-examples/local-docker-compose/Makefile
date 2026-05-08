SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

CONTAINER ?= open-mpic-coordinator-1
ITERATIONS ?= 10
DELAY ?= 0.2
CHECK_TYPE ?= both
OUTCOME ?= both
DOMAINS ?= example.com,wikipedia.org,github.com,letsencrypt.org,cloudflare.com
PERSPECTIVE_COUNT ?= 2
QUORUM_COUNT ?= 2
LOCAL_CORE_PATH ?=
COMPOSE_CMD ?= docker compose -f compose.dev.yaml -f compose.otel.yaml

.PHONY: help teardown teardown-wipe traffic traffic-random traffic-mixed-caa traffic-controlled traffic-caa-valid traffic-caa-invalid traffic-dcv-valid traffic-dcv-invalid otel-demo otel-demo-pypi otel-demo-local

help:
	@printf "Local Docker Compose helpers\n\n"
	@printf "Lifecycle:\n"
	@printf "  make teardown          # stop and remove local dev + otel compose resources\n\n"
	@printf "  make teardown-wipe     # same as teardown, plus remove compose volumes\n\n"
	@printf "Traffic generation:\n"
	@printf "  make traffic            # deterministic valid+invalid CAA/DCV traffic\n"
	@printf "  make traffic-random     # generic traffic across a domain list\n"
	@printf "  make traffic-mixed-caa  # deterministic CAA valid+invalid only\n"
	@printf "  make traffic-caa-valid  # deterministic CAA valid only\n"
	@printf "  make traffic-caa-invalid\n"
	@printf "  make traffic-dcv-valid\n"
	@printf "  make traffic-dcv-invalid\n"
	@printf "  make otel-demo          # generate success-path OTEL telemetry with all checkers running\n"
	@printf "\n"
	@printf "Aliases:\n"
	@printf "  make otel-demo-pypi            # same as otel-demo (pinned open-mpic-core PyPI package)\n"
	@printf "  make otel-demo-local           # healthy-path demo using local editable open-mpic-core\n"
	@printf "\n"
	@printf "Overrides:\n"
	@printf "  make traffic ITERATIONS=50 DELAY=0.1\n"
	@printf "  make traffic-random CHECK_TYPE=caa DOMAINS=good.test.internal\n"
	@printf "  make traffic CONTAINER=open-mpic-coordinator-1\n"
	@printf "  make otel-demo ITERATIONS=8 DELAY=0.05\n"
	@printf "  make otel-demo-local LOCAL_CORE_PATH=../../../../open-mpic-core-python\n"

teardown:
	@$(COMPOSE_CMD) down --remove-orphans
	@echo 'Local compose stack has been torn down.'

teardown-wipe:
	@$(COMPOSE_CMD) down --remove-orphans -v
	@echo 'Local compose stack and volumes have been torn down.'

traffic: traffic-controlled

traffic-random:
	./generate_traffic.sh \
		--container "$(CONTAINER)" \
		--iterations "$(ITERATIONS)" \
		--delay "$(DELAY)" \
		--check-type "$(CHECK_TYPE)" \
		--domains "$(DOMAINS)" \
		--perspective-count "$(PERSPECTIVE_COUNT)" \
		--quorum-count "$(QUORUM_COUNT)"

traffic-mixed-caa:
	./generate_mixed_caa_traffic.sh \
		--container "$(CONTAINER)" \
		--iterations "$(ITERATIONS)" \
		--delay "$(DELAY)" \
		--perspective-count "$(PERSPECTIVE_COUNT)" \
		--quorum-count "$(QUORUM_COUNT)"

traffic-controlled:
	./generate_controlled_traffic.sh \
		--container "$(CONTAINER)" \
		--iterations "$(ITERATIONS)" \
		--delay "$(DELAY)" \
		--check-type "$(CHECK_TYPE)" \
		--outcome "$(OUTCOME)" \
		--perspective-count "$(PERSPECTIVE_COUNT)" \
		--quorum-count "$(QUORUM_COUNT)"

traffic-caa-valid:
	$(MAKE) traffic-controlled CHECK_TYPE=caa OUTCOME=valid ITERATIONS="$(ITERATIONS)" DELAY="$(DELAY)"

traffic-caa-invalid:
	$(MAKE) traffic-controlled CHECK_TYPE=caa OUTCOME=invalid ITERATIONS="$(ITERATIONS)" DELAY="$(DELAY)"

traffic-dcv-valid:
	$(MAKE) traffic-controlled CHECK_TYPE=dcv OUTCOME=valid ITERATIONS="$(ITERATIONS)" DELAY="$(DELAY)"

traffic-dcv-invalid:
	$(MAKE) traffic-controlled CHECK_TYPE=dcv OUTCOME=invalid ITERATIONS="$(ITERATIONS)" DELAY="$(DELAY)"

otel-demo:
	@echo 'Generating success-path OTEL telemetry with all checkers running...'; \
	./generate_controlled_traffic.sh \
		--container "$(CONTAINER)" \
		--iterations "$(ITERATIONS)" \
		--delay "$(DELAY)" \
		--check-type both \
		--outcome valid \
		--perspective-count "$(PERSPECTIVE_COUNT)" \
		--quorum-count "$(QUORUM_COUNT)" >/dev/null; \
	echo 'OTEL telemetry should now be present in recent Grafana/Loki/Tempo views.'

otel-demo-pypi:
	@$(MAKE) otel-demo

otel-demo-local:
	@if [[ -z "$(LOCAL_CORE_PATH)" ]]; then \
		echo 'LOCAL_CORE_PATH is required for otel-demo-local'; \
		exit 1; \
	fi
	@LOCAL_CORE_PATH="$(LOCAL_CORE_PATH)" $(MAKE) otel-demo
