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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEMVER_SCRIPT="${SCRIPT_DIR}/semver.sh"

if [ ! -f "$SEMVER_SCRIPT" ]; then
  echo "Unable to find semver helper at ${SEMVER_SCRIPT}" >&2
  exit 1
fi

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

try:
    import tomllib as toml_loader
except ModuleNotFoundError:
    try:
        import tomli as toml_loader
    except ModuleNotFoundError:
        print(
            "Unable to parse TOML: need Python 3.11+ (tomllib) or installed tomli package",
            file=sys.stderr,
        )
        raise SystemExit(2)

path = pathlib.Path(sys.argv[1])

try:
    raw_text = path.read_text(encoding="utf-8")
except Exception as exc:
    print(f"Unable to read TOML file {path}: {exc}", file=sys.stderr)
    raise SystemExit(2)

try:
    data = toml_loader.loads(raw_text)
except Exception as exc:
    print(f"Invalid TOML in {path}: {exc}", file=sys.stderr)
    raise SystemExit(2)

project = data.get("project")
if not isinstance(project, dict):
    print(f"Missing [project] table in {path}", file=sys.stderr)
    raise SystemExit(2)

version = project.get("version")
if not isinstance(version, str) or not version.strip():
    print(f"Missing [project].version in {path}", file=sys.stderr)
    raise SystemExit(2)

print(version.strip())
PY
}

project_tag_from_version() {
  local project_version="$1"
  local semver_parse_output
  local project_tag=""

  semver_parse_output=$(sh "$SEMVER_SCRIPT" parse "$project_version")

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
    expected_tag=$(sh "$SEMVER_SCRIPT" "bump-${bump_kind}" "$release_tag")
    expected_tag_patch=$(sh "$SEMVER_SCRIPT" "bump-patch" "$release_tag")
    expected_tag_minor=$(sh "$SEMVER_SCRIPT" "bump-minor" "$release_tag")
    expected_tag_major=$(sh "$SEMVER_SCRIPT" "bump-major" "$release_tag")

    matches_expected="false"
    if [ "$project_tag" = "$expected_tag" ]; then
      matches_expected="true"
    fi

    echo "latest-tag=$release_tag"
    echo "bump-kind=$bump_kind"
    echo "project-version=$project_version"
    echo "project-tag=$project_tag"
    echo "expected-tag=$expected_tag"
    echo "expected-version=${expected_tag#v}"
    echo "expected-version-patch=${expected_tag_patch#v}"
    echo "expected-version-minor=${expected_tag_minor#v}"
    echo "expected-version-major=${expected_tag_major#v}"
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