# Install Python plotting dependencies if not already installed

# Ensure load-test dependencies are installed using Hatch
.PHONY: deps
deps:
	hatch env create load-test || hatch env update load-test

# Makefile for orchestrating Docker-based integration and load tests.

DCV_COMPOSE_FILE := docker-compose.dcv-load-test.yml
DOCKER_COMPOSE := docker compose
DCV_SERVICE_NAME := dcv-service
TEST_SERVER_HOSTNAME := test-server
TESTDIR := load-tests/dcv-http-01
TITLE := DCV-HTTP-01 Latency

.PHONY: all

all: test


# Main test target: starts services, runs the load test, and cleans up.
.PHONY: test
test:
	@echo "--- Starting services... ---"
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) up -d $(DCV_SERVICE_NAME) $(TEST_SERVER_HOSTNAME)
	@echo "\n--- Running load test... ---"
	mkdir -p $(TESTDIR)/output
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) run --rm vegeta-load-tester > $(TESTDIR)/output/results.bin
	@echo "\n--- Test complete. Cleaning up... ---"
	make clean
	@echo "\n--- Done. ---"

# Like 'test', but leaves containers running for manual debugging after the test.
.PHONY: test-debug
test-debug:
	@echo "--- Starting services... ---"
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) up -d $(DCV_SERVICE_NAME) $(TEST_SERVER_HOSTNAME)
	@echo "\n--- Running load test... ---"
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) run --rm load-tester
	@echo "\n--- Test complete. Containers are still running for manual inspection. ---"

# Create Report
.PHONY: report
report: deps
	@echo "--- Generating text report from results... ---"
	vegeta report --type=text < $(TESTDIR)/output/results.bin | tee $(TESTDIR)/output/vegeta-report.txt
	@echo "--- Generating JSON report from results... ---"
	vegeta encode $(TESTDIR)/output/results.bin > $(TESTDIR)/output/results.jsonl
	@echo "--- Report generation complete. Check results.json for details. ---"
	@echo "--- Generating latency timeseries plot... ---"
	./load-tests/chart.py --testdir $(TESTDIR) --title "$(TITLE)"
	@echo "--- Plot saved as $(TESTDIR)/output/latency-timeseries-plot.png ---"
	@if [ -n "$$GITHUB_STEP_SUMMARY" ]; then \
	  echo '## Vegeta Text Report' >> $$GITHUB_STEP_SUMMARY; \
	  echo '\n\n```' >> $$GITHUB_STEP_SUMMARY; \
	  cat $(TESTDIR)/output/vegeta-report.txt >> $$GITHUB_STEP_SUMMARY; \
	  echo '```' >> $$GITHUB_STEP_SUMMARY; \
	fi

.PHONY: clean
clean:
	@echo "--- Stopping services and removing volumes... ---"
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) down -v --remove-orphans

# Build all images from scratch (no cache)
.PHONY: build
build:
	@echo "--- Rebuilding all images... ---"
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) build --no-cache

# A target to manually start services for debugging.
.PHONY: start
start:
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) up -d

# A target to manually stop services.
.PHONY: stop
stop:
	$(DOCKER_COMPOSE) -f $(DCV_COMPOSE_FILE) down --remove-orphans
