#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/release-version-intent.sh validate-intent <pyproject-path> <pr-labels-json>
  scripts/release-version-intent.sh project-tag <pyproject-path>

Commands:
  validate-intent  Prints key=value pairs used to validate release intent.
  project-tag      Prints project-version and release-tag from pyproject.toml.
EOF
}

read_project_version() {
  local pyproject_path="$1"
  local python_cmd

  if command -v python3 >/dev/null 2>&1; then
    python_cmd="python3"
  elif command -v python >/dev/null 2>&1; then
    python_cmd="python"
  else
    echo "Python is required to parse TOML (python3 or python not found)" >&2
    exit 1
  fi

  "$python_cmd" - "$pyproject_path" <<'PY'
import pathlib
import sys
import tomllib

path = pathlib.Path(sys.argv[1])
data = tomllib.loads(path.read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
}

project_tag_from_version() {
  local project_version="$1"
  local semver_parse_output
  local project_tag=""

  semver_parse_output=$(sh scripts/semver.sh parse "$project_version")

  while IFS='=' read -r key value; do
    if [ "$key" = "tag" ]; then
      project_tag="$value"
      break
    fi
  done <<EOF
$semver_parse_output
EOF

  if [ -z "$project_tag" ]; then
    echo "Unable to parse release tag from project version: $project_version" >&2
    exit 1
  fi

  echo "$project_tag"
}

detect_bump_kind() {
  local pr_labels_json="$1"
  local bump_kind="patch"
  local has_release_label="false"

  if printf "%s" "$pr_labels_json" | grep -Eq '"release:major"'; then
    bump_kind="major"
    has_release_label="true"
  elif printf "%s" "$pr_labels_json" | grep -Eq '"release:minor"'; then
    bump_kind="minor"
    has_release_label="true"
  elif printf "%s" "$pr_labels_json" | grep -Eq '"release:patch"'; then
    bump_kind="patch"
    has_release_label="true"
  fi

  echo "$bump_kind,$has_release_label"
}

latest_release_tag() {
  if tag=$(gh release view --json tagName --template '{{.tagName}}' 2>/dev/null); then
    printf "%s\n" "$tag"
  else
    printf "v0.0.0\n"
  fi
}

if [ "$#" -lt 2 ]; then
  usage >&2
  exit 2
fi

command="$1"
pyproject_path="$2"

case "$command" in
  validate-intent)
    if [ "$#" -ne 3 ]; then
      usage >&2
      exit 2
    fi

    pr_labels_json="$3"
    project_version=$(read_project_version "$pyproject_path")
    if [ -z "$project_version" ]; then
      echo "Unable to read project.version from $pyproject_path" >&2
      exit 1
    fi

    project_tag=$(project_tag_from_version "$project_version")
    release_tag=$(latest_release_tag)
    bump_data=$(detect_bump_kind "$pr_labels_json")
    bump_kind="${bump_data%%,*}"
    has_release_label="${bump_data##*,}"
    expected_tag=$(sh scripts/semver.sh "bump-${bump_kind}" "$release_tag")

    matches_expected="false"
    if [ "$project_tag" = "$expected_tag" ]; then
      matches_expected="true"
    fi

    echo "latest-tag=$release_tag"
    echo "bump-kind=$bump_kind"
    echo "project-version=$project_version"
    echo "project-tag=$project_tag"
    echo "expected-tag=$expected_tag"
    echo "has-release-label=$has_release_label"
    echo "matches-expected=$matches_expected"
    ;;
  project-tag)
    if [ "$#" -ne 2 ]; then
      usage >&2
      exit 2
    fi

    project_version=$(read_project_version "$pyproject_path")
    if [ -z "$project_version" ]; then
      echo "Unable to read project.version from $pyproject_path" >&2
      exit 1
    fi

    release_tag=$(project_tag_from_version "$project_version")
    echo "project-version=$project_version"
    echo "release-tag=$release_tag"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac