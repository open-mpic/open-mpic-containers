# Makefile for orchestrating Docker-based integration and load tests.

COMPOSE_FILE := docker-compose.test.yml
DOCKER_COMPOSE := docker compose
SERVICE_NAME := dcv-service
TEST_SERVER_HOSTNAME := test-server

.PHONY: all

all: test


# Main test target: starts services, runs the load test, and cleans up.
.PHONY: test
test:
	@echo "--- Starting services... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d $(SERVICE_NAME) $(TEST_SERVER_HOSTNAME)
	@echo "\n--- Running load test... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) run --rm load-tester
	@echo "\n--- Test complete. Cleaning up... ---"
	make clean
	@echo "\n--- Done. ---"

# Like 'test', but leaves containers running for manual debugging after the test.
.PHONY: test-debug
test-debug:
	@echo "--- Starting services... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d $(SERVICE_NAME) $(TEST_SERVER_HOSTNAME)
	@echo "\n--- Running load test... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) run --rm load-tester
	@echo "\n--- Test complete. Containers are still running for manual inspection. ---"


.PHONY: clean
clean:
	@echo "--- Stopping services and removing volumes... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v --remove-orphans

# Build all images from scratch (no cache)
.PHONY: build
build:
	@echo "--- Rebuilding all images... ---"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build --no-cache

# A target to manually start services for debugging.
.PHONY: start
start:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d

# A target to manually stop services.
.PHONY: stop
stop:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down --remove-orphans
