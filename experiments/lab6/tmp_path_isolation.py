"""Run the file test several times and compare the project tree before/after.

Usage: python experiments/lab6/tmp_path_isolation.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {".git", "__pycache__", ".venv", "node_modules"}


def snapshot() -> set[str]:
    return {
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*")
        if not (set(p.relative_to(ROOT).parts) & SKIP)
    }


def main() -> None:
    before = snapshot()

    for attempt in range(1, 4):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "experiments/lab6/test_exp6_tmp_path.py"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        last = result.stdout.strip().splitlines()[-1]
        print(f"run {attempt}: {last}")

    after = snapshot()
    print("files added to the repository:", sorted(after - before))
    print("files removed from the repository:", sorted(before - after))


if __name__ == "__main__":
    main()
