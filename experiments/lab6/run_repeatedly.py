"""Run one pytest node id many times and count passes and failures.

Usage: python experiments/lab6/run_repeatedly.py <node id> [times]
"""

import subprocess
import sys


def main() -> None:
    node = sys.argv[1]
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    passed = 0

    for _ in range(times):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
            capture_output=True,
            check=False,
        )
        passed += result.returncode == 0

    print(f"{node}: passed {passed} of {times}, failed {times - passed}")


if __name__ == "__main__":
    main()
