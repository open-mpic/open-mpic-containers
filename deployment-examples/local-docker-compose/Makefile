CONTAINER ?= open-mpic-coordinator-1
ITERATIONS ?= 10
DELAY ?= 0.2
CHECK_TYPE ?= both
OUTCOME ?= both
DOMAINS ?= example.com,wikipedia.org,github.com,letsencrypt.org,cloudflare.com
PERSPECTIVE_COUNT ?= 2
QUORUM_COUNT ?= 2

.PHONY: help traffic traffic-random traffic-mixed-caa traffic-controlled traffic-caa-valid traffic-caa-invalid traffic-dcv-valid traffic-dcv-invalid otel-logs-demo

help:
	@printf "Local Docker Compose helpers\n\n"
	@printf "Traffic generation:\n"
	@printf "  make traffic            # deterministic valid+invalid CAA/DCV traffic\n"
	@printf "  make traffic-random     # generic traffic across a domain list\n"
	@printf "  make traffic-mixed-caa  # deterministic CAA valid+invalid only\n"
	@printf "  make traffic-caa-valid  # deterministic CAA valid only\n"
	@printf "  make traffic-caa-invalid\n"
	@printf "  make traffic-dcv-valid\n"
	@printf "  make traffic-dcv-invalid\n"
	@printf "  make otel-logs-demo     # force short-lived checker failures to emit OTEL warning logs\n\n"
	@printf "Overrides:\n"
	@printf "  make traffic ITERATIONS=50 DELAY=0.1\n"
	@printf "  make traffic-random CHECK_TYPE=caa DOMAINS=good.test.internal\n"
	@printf "  make traffic CONTAINER=open-mpic-coordinator-1\n"
	@printf "  make otel-logs-demo ITERATIONS=8 DELAY=0.05\n"

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

otel-logs-demo:
	@set -euo pipefail; \
	compose_cmd='docker compose -f compose.dev.yaml -f compose.otel.yaml'; \
	echo 'Stopping dcv_checker_1 to induce remote checker warnings...'; \
	$$compose_cmd stop dcv_checker_1 >/dev/null; \
	cleanup() { \
		echo 'Restoring dcv_checker_1...'; \
		$$compose_cmd start dcv_checker_1 >/dev/null; \
	}; \
	trap cleanup EXIT; \
	./generate_controlled_traffic.sh \
		--container "$(CONTAINER)" \
		--iterations "$(ITERATIONS)" \
		--delay "$(DELAY)" \
		--check-type dcv \
		--outcome both \
		--perspective-count "$(PERSPECTIVE_COUNT)" \
		--quorum-count "$(QUORUM_COUNT)" >/dev/null; \
	echo 'OTEL warning/error logs should now be present in recent Loki time range.'
