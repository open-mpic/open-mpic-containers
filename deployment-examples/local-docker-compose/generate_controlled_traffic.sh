#!/usr/bin/env bash
set -euo pipefail

# Generates deterministic local traffic for all MPIC decision combinations:
# - CAA valid / invalid
# - DCV valid / invalid

CONTAINER_NAME="open-mpic-coordinator-1"
ITERATIONS=10
DELAY_SECONDS=0.2
CHECK_TYPE="both"       # both|caa|dcv
OUTCOME="both"          # both|valid|invalid
PERSPECTIVE_COUNT=2
QUORUM_COUNT=2

VALID_DOMAIN="valid.test.internal"
INVALID_DOMAIN="invalid.test.internal"

DCV_DNS_PREFIX="_validation"
DCV_VALID_CHALLENGE="dcv-valid-token"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --container NAME         Coordinator container name (default: ${CONTAINER_NAME})
  --iterations N           Number of rounds to send (default: ${ITERATIONS})
  --delay SECONDS          Delay between requests (default: ${DELAY_SECONDS})
  --check-type TYPE        one of: both, caa, dcv (default: ${CHECK_TYPE})
  --outcome TYPE           one of: both, valid, invalid (default: ${OUTCOME})
  --perspective-count N    Orchestration perspective_count (default: ${PERSPECTIVE_COUNT})
  --quorum-count N         Orchestration quorum_count (default: ${QUORUM_COUNT})
  -h, --help               Show this help message

Examples:
  $0
  $0 --check-type dcv --outcome invalid --iterations 20 --delay 0.1
  $0 --check-type caa --outcome valid --iterations 30
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --iterations)
      ITERATIONS="$2"
      shift 2
      ;;
    --delay)
      DELAY_SECONDS="$2"
      shift 2
      ;;
    --check-type)
      CHECK_TYPE="$2"
      shift 2
      ;;
    --outcome)
      OUTCOME="$2"
      shift 2
      ;;
    --perspective-count)
      PERSPECTIVE_COUNT="$2"
      shift 2
      ;;
    --quorum-count)
      QUORUM_COUNT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if ! [[ "$CHECK_TYPE" =~ ^(both|caa|dcv)$ ]]; then
  echo "Invalid --check-type: ${CHECK_TYPE}. Use one of: both, caa, dcv"
  exit 1
fi

if ! [[ "$OUTCOME" =~ ^(both|valid|invalid)$ ]]; then
  echo "Invalid --outcome: ${OUTCOME}. Use one of: both, valid, invalid"
  exit 1
fi

send_caa() {
  local domain="$1"
  docker exec "$CONTAINER_NAME" curl -s -X POST http://localhost/mpic \
    -H "Content-Type: application/json" \
    -d "{\"domain_or_ip_target\":\"${domain}\",\"check_type\":\"caa\",\"orchestration_parameters\":{\"perspective_count\":${PERSPECTIVE_COUNT},\"quorum_count\":${QUORUM_COUNT}}}" \
    > /dev/null
}

send_dcv() {
  local domain="$1"
  docker exec "$CONTAINER_NAME" curl -s -X POST http://localhost/mpic \
    -H "Content-Type: application/json" \
    -d "{\"domain_or_ip_target\":\"${domain}\",\"check_type\":\"dcv\",\"dcv_check_parameters\":{\"validation_method\":\"dns-change\",\"dns_name_prefix\":\"${DCV_DNS_PREFIX}\",\"dns_record_type\":\"TXT\",\"challenge_value\":\"${DCV_VALID_CHALLENGE}\",\"require_exact_match\":true},\"orchestration_parameters\":{\"perspective_count\":${PERSPECTIVE_COUNT},\"quorum_count\":${QUORUM_COUNT}}}" \
    > /dev/null
}

declare -a TARGETS=()
if [[ "$OUTCOME" == "both" || "$OUTCOME" == "valid" ]]; then
  TARGETS+=("valid:${VALID_DOMAIN}")
fi
if [[ "$OUTCOME" == "both" || "$OUTCOME" == "invalid" ]]; then
  TARGETS+=("invalid:${INVALID_DOMAIN}")
fi

echo "Target container : ${CONTAINER_NAME}"
echo "Iterations       : ${ITERATIONS}"
echo "Delay (seconds)  : ${DELAY_SECONDS}"
echo "Check type       : ${CHECK_TYPE}"
echo "Outcome filter   : ${OUTCOME}"
echo "Domains          : ${VALID_DOMAIN} (valid), ${INVALID_DOMAIN} (invalid)"
echo

sent=0
for ((i=1; i<=ITERATIONS; i++)); do
  for target in "${TARGETS[@]}"; do
    outcome_label="${target%%:*}"
    domain="${target#*:}"

    if [[ "$CHECK_TYPE" == "both" || "$CHECK_TYPE" == "caa" ]]; then
      send_caa "$domain"
      sent=$((sent + 1))
      echo "[$i/${ITERATIONS}] sent CAA (${outcome_label}) for ${domain}"
      sleep "$DELAY_SECONDS"
    fi

    if [[ "$CHECK_TYPE" == "both" || "$CHECK_TYPE" == "dcv" ]]; then
      send_dcv "$domain"
      sent=$((sent + 1))
      echo "[$i/${ITERATIONS}] sent DCV (${outcome_label}) for ${domain}"
      sleep "$DELAY_SECONDS"
    fi
  done
done

echo
echo "Done. Sent ${sent} total requests."
echo "Check Grafana: http://localhost:3000"