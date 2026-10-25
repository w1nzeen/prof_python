"""Experiment 6: a file test must not depend on previous runs."""

from pathlib import Path


def test_writes_only_inside_tmp_path(tmp_path: Path) -> None:
    assert list(tmp_path.iterdir()) == []  # always empty at the start

    target = tmp_path / "result.txt"
    target.write_text("data", encoding="utf-8")

    assert target.read_text(encoding="utf-8") == "data"
