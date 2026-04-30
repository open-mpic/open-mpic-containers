#!/usr/bin/env bash
set -euo pipefail

# Generates a deterministic mix of valid and invalid CAA results.
#
# valid.test.internal resolves to an allowed CAA value from both split-DNS
# perspectives, while invalid.test.internal resolves to mismatched CAA values
# across perspectives and fails quorum.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VALID_DOMAIN="valid.test.internal"
INVALID_DOMAIN="invalid.test.internal"

usage() {
  cat <<EOF
Usage: $0 [generate_traffic.sh options]

Runs deterministic CAA traffic for:
  - ${VALID_DOMAIN}   -> expected mpic_is_valid=True
  - ${INVALID_DOMAIN} -> expected mpic_is_valid=False

Examples:
  $0
  $0 --iterations 20 --delay 0.2
  $0 --container open-mpic-coordinator-1 --perspective-count 2 --quorum-count 2
EOF
}

for arg in "$@"; do
  if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
    usage
    exit 0
  fi
done

exec "${SCRIPT_DIR}/generate_controlled_traffic.sh" \
  --check-type caa \
  --outcome both \
  "$@"