#!/bin/bash

# Validates that all .python-version files match the expected Python version.
# Can be run locally or in GitHub Actions.
#
# Usage:
#   ./scripts/validate-python-versions.sh EXPECTED_VERSION
#
# Arguments:
#   EXPECTED_VERSION: Required. In GitHub Actions, can be passed via PYTHON_VERSION env var
#                     as: ./scripts/validate-python-versions.sh ${{ env.PYTHON_VERSION }}

set -e

# Determine expected version
if [ -n "$1" ]; then
  EXPECTED_VERSION="$1"
elif [ -n "${PYTHON_VERSION:-}" ]; then
  # PYTHON_VERSION can be set in GitHub Actions workflow
  EXPECTED_VERSION="$PYTHON_VERSION"
else
  echo "❌ Error: Expected Python version must be provided as argument or PYTHON_VERSION env var"
  exit 1
fi

VERSIONS_MATCH=true

echo "Validating Python versions..."
echo "Expected version: $EXPECTED_VERSION"
echo ""

for file in api-implementation/src/mpic_*/.python-version; do
  if [ ! -f "$file" ]; then
    continue
  fi
  
  FILE_VERSION=$(cat "$file" | tr -d ' \n')
  
  if [ "$FILE_VERSION" = "$EXPECTED_VERSION" ]; then
    echo "✅ $file: $FILE_VERSION"
  else
    echo "❌ $file: $FILE_VERSION (expected $EXPECTED_VERSION)"
    VERSIONS_MATCH=false
  fi
done

echo ""

if [ "$VERSIONS_MATCH" = false ]; then
  echo "❌ Python version validation failed - .python-version files do not match expected version"
  exit 1
fi

echo "✅ All .python-version files match expected version"
