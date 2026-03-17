#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  scripts/semver.sh parse <version>
  scripts/semver.sh bump-major <version>
  scripts/semver.sh bump-minor <version>
  scripts/semver.sh bump-patch <version>

Accepted versions:
  X.Y.Z or vX.Y.Z

Commands:
  parse       Print parsed fields as key=value lines.
  bump-major  Print next major release as v(X+1).0.0
  bump-minor  Print next minor release as vX.(Y+1).0
  bump-patch  Print next patch release as vX.Y.(Z+1)
EOF
}

if [ "$#" -ne 2 ]; then
  usage >&2
  exit 2
fi

cmd="$1"
input="$2"

normalized=$(printf "%s" "$input" | sed 's/^[vV]//')

if ! printf "%s" "$normalized" | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'; then
  echo "Invalid semantic version: $input" >&2
  exit 1
fi

major=$(printf "%s" "$normalized" | cut -d. -f1)
minor=$(printf "%s" "$normalized" | cut -d. -f2)
patch=$(printf "%s" "$normalized" | cut -d. -f3)

case "$cmd" in
  parse)
    echo "input=$input"
    echo "normalized=$normalized"
    echo "major=$major"
    echo "minor=$minor"
    echo "patch=$patch"
    echo "tag=v$normalized"
    ;;
  bump-major)
    next_major=$((major + 1))
    next="${next_major}.0.0"
    echo "v$next"
    ;;
  bump-minor)
    next_minor=$((minor + 1))
    next="${major}.${next_minor}.0"
    echo "v$next"
    ;;
  bump-patch)
    next_patch=$((patch + 1))
    next="${major}.${minor}.${next_patch}"
    echo "v$next"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
