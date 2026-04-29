#!/usr/bin/env bash
set -euo pipefail

# Generates MPIC traffic against the local coordinator container.
#
# Usage examples:
#   ./generate_traffic.sh
#   ./generate_traffic.sh --iterations 20 --delay 1
#   ./generate_traffic.sh --check-type caa --iterations 50
#   ./generate_traffic.sh --container open-mpic-coordinator-1 --domains "example.com,github.com"

CONTAINER_NAME="open-mpic-coordinator-1"
ITERATIONS=10
DELAY_SECONDS=0.5
CHECK_TYPE="both"   # both|caa|dcv
DOMAINS_CSV="example.com,wikipedia.org,github.com,letsencrypt.org,cloudflare.com"
PERSPECTIVE_COUNT=2
QUORUM_COUNT=2

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --container NAME         Coordinator container name (default: ${CONTAINER_NAME})
  --iterations N           Number of rounds to send (default: ${ITERATIONS})
  --delay SECONDS          Delay between requests (default: ${DELAY_SECONDS})
  --check-type TYPE        one of: both, caa, dcv (default: ${CHECK_TYPE})
  --domains CSV            Comma-separated domains (default: ${DOMAINS_CSV})
  --perspective-count N    Orchestration perspective_count (default: ${PERSPECTIVE_COUNT})
  --quorum-count N         Orchestration quorum_count (default: ${QUORUM_COUNT})
  -h, --help               Show this help message
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
    --domains)
      DOMAINS_CSV="$2"
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

IFS=',' read -r -a DOMAINS <<< "$DOMAINS_CSV"
if [[ ${#DOMAINS[@]} -eq 0 ]]; then
  echo "No domains provided"
  exit 1
fi

echo "Target container : ${CONTAINER_NAME}"
echo "Iterations       : ${ITERATIONS}"
echo "Delay (seconds)  : ${DELAY_SECONDS}"
echo "Check type       : ${CHECK_TYPE}"
echo "Domains          : ${DOMAINS_CSV}"
echo

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
    -d "{\"domain_or_ip_target\":\"${domain}\",\"check_type\":\"dcv\",\"dcv_check_parameters\":{\"validation_method\":\"http-generic\",\"http_token_path\":\"/.well-known/pki-validation/test.txt\",\"challenge_value\":\"test123\"},\"orchestration_parameters\":{\"perspective_count\":${PERSPECTIVE_COUNT},\"quorum_count\":${QUORUM_COUNT}}}" \
    > /dev/null
}

sent=0
for ((i=1; i<=ITERATIONS; i++)); do
  for domain in "${DOMAINS[@]}"; do
    if [[ "$CHECK_TYPE" == "both" || "$CHECK_TYPE" == "caa" ]]; then
      send_caa "$domain"
      sent=$((sent + 1))
      echo "[$i/${ITERATIONS}] sent CAA for ${domain}"
      sleep "$DELAY_SECONDS"
    fi

    if [[ "$CHECK_TYPE" == "both" || "$CHECK_TYPE" == "dcv" ]]; then
      send_dcv "$domain"
      sent=$((sent + 1))
      echo "[$i/${ITERATIONS}] sent DCV for ${domain}"
      sleep "$DELAY_SECONDS"
    fi
  done
done

echo
echo "Done. Sent ${sent} total requests."
echo "Check Grafana: http://localhost:3000"
