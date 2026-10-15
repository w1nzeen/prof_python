"""CI-like command: lint, static type check and tests.

Usage: python scripts/check.py
"""

import subprocess
import sys

STEPS: list[tuple[str, list[str]]] = [
    ("ruff", [sys.executable, "-m", "ruff", "check", "src", "tests"]),
    ("mypy (strict)", [sys.executable, "-m", "mypy", "src", "tests"]),
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
]


def main() -> int:
    for name, command in STEPS:
        print(f"== {name} ==", flush=True)
        result = subprocess.run(command, check=False)

        if result.returncode != 0:
            print(f"FAILED: {name}")
            return result.returncode

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
