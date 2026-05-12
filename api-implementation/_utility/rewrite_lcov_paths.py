from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python _utility/rewrite_lcov_paths.py <lcov_path> <workspace_prefix>")
        return 1

    lcov_path = Path(sys.argv[1])
    workspace_prefix = sys.argv[2].rstrip("/")

    if not lcov_path.exists():
        print(f"LCOV file not found: {lcov_path}")
        return 1

    content = lcov_path.read_text()
    lines = content.splitlines(keepends=True)

    rewritten = "".join(f"SF:{workspace_prefix}/{line[3:]}" if line.startswith("SF:src/") else line for line in lines)

    lcov_path.write_text(rewritten)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
