"""Experiments of laboratory work 5."""

import csv
import hashlib
import io
import random
import sys
import tempfile
import traceback
import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TypeVar

from equipment_manager.importer.config import (
    AppConfig,
    InputConfig,
    LoggingConfig,
    OutputConfig,
    ProcessingConfig,
    load_and_validate,
)
from equipment_manager.importer.exceptions import (
    ApplicationError,
    DataExportError,
    RecordValidationError,
)
from equipment_manager.importer.exporters import JsonExporter
from equipment_manager.importer.main import main as importer_main
from equipment_manager.importer.models import EquipmentRecord
from equipment_manager.importer.readers import CsvImporter
from equipment_manager.importer.services import ImportStatistics, run_import
from equipment_manager.importer.utils import temporary_path
from equipment_manager.importer.validators import (
    ValidationRules,
    validate_record,
)

T = TypeVar("T")

TYPES = ("Laptop", "Monitor", "Printer", "Router", "Server", "Keyboard")
MANUFACTURERS = ("Lenovo", "Dell", "HP", "Asus", "Acer", "TP-Link")
HEADER = ["inventory_number", "type", "manufacturer", "model", "value"]
MEGABYTE = 1024 * 1024
INVALID_ROWS = (
    ["PC-X", "Laptop", "Dell", "XPS", "1000"],  # bad inventory number
    ["", "Laptop", "Dell", "XPS", "1000"],  # empty inventory number
    ["PC-1", "Tablet", "Dell", "XPS", "1000"],  # unknown type
    ["PC-1", "Laptop", "Apple", "XPS", "1000"],  # unknown manufacturer
    ["PC-1", "Laptop", "Dell", "", "1000"],  # empty model
    ["PC-1", "Laptop", "Dell", "XPS", "abc"],  # not numeric
    ["PC-1", "Laptop", "Dell", "XPS", "-5"],  # negative
    ["PC-1", "Laptop", "Dell", "XPS"],  # missing field
    ["PC-1", "Laptop", "Dell", "XPS", "1", "extra"],  # extra field
    ["PC-1", "Laptop", "Dell", "XPS", "nan"],  # not finite
)


def make_config(
    directory: Path,
    input_path: Path,
    *,
    skip_invalid: bool = True,
    output_name: str = "result.json",
    with_logs: bool = False,
) -> AppConfig:
    return AppConfig(
        version=1,
        input=InputConfig(input_path),
        output=OutputConfig(directory / output_name),
        processing=ProcessingConfig(
            skip_invalid=skip_invalid,
            minimum_value=0.0,
            allowed_types=TYPES,
            allowed_manufacturers=MANUFACTURERS,
        ),
        logging=LoggingConfig(
            path=directory / "app.log" if with_logs else None,
            errors_path=directory / "errors.csv" if with_logs else None,
        ),
    )


def generate_csv(
    path: Path,
    valid: int,
    invalid: int = 0,
    seed: int = 42,
) -> None:
    """Write `valid` correct rows and `invalid` broken ones (evenly spread)."""
    rng = random.Random(seed)
    step = max(1, (valid + invalid) // invalid) if invalid else 0
    broken = 0

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        written_valid = 0
        index = 0

        while written_valid < valid or broken < invalid:
            index += 1

            if step and broken < invalid and index % step == step // 2:
                writer.writerow(INVALID_ROWS[broken % len(INVALID_ROWS)])
                broken += 1
            elif written_valid < valid:
                written_valid += 1
                writer.writerow(
                    [
                        f"PC-{written_valid:06d}",
                        rng.choice(TYPES),
                        rng.choice(MANUFACTURERS),
                        f"Model-{rng.randint(1, 99)}",
                        round(rng.uniform(300, 80000), 2),
                    ]
                )


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))

    for row in rows:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)))


# --------------------------------------------------- experiment 1


def experiment_strict_vs_tolerant() -> None:
    print("Experiment 1. Strict vs tolerant (1000 valid + 10 invalid records)")
    results: list[list[str]] = []

    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        source = directory / "input.csv"
        generate_csv(source, valid=1000, invalid=10)

        for label, skip in (("Strict", False), ("Tolerant", True)):
            config = make_config(
                directory,
                source,
                skip_invalid=skip,
                output_name=f"{label.lower()}.json",
                with_logs=True,
            )
            statistics = ImportStatistics()

            try:
                with redirect_stderr(io.StringIO()):
                    run_import(config, statistics=statistics)
                ending = "completed (exit 0)"
            except RecordValidationError as error:
                ending = f"stopped at line {error.line_number} (exit 1)"

            results.append(
                [
                    label,
                    str(statistics.total),
                    str(statistics.valid),
                    str(statistics.invalid),
                    str(statistics.exported),
                    "yes" if config.output.path.exists() else "no",
                    ending,
                ]
            )

    print_table(
        ["Mode", "Processed", "Valid", "Invalid", "Exported", "Output file", "Ending"],
        results,
    )


# --------------------------------------------------- experiment 2


def eager_import(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def streaming_import(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def consume_eager(path: Path) -> int:
    return len(eager_import(path))


def consume_streaming(path: Path) -> int:
    count = 0

    for _ in streaming_import(path):  # the generator must be consumed
        count += 1

    return count


def consume_pipeline(path: Path) -> int:
    config = make_config(path.parent, path, output_name="pipeline.json")

    return run_import(config).exported


def timed(function: Callable[[Path], T], path: Path) -> tuple[T, float]:
    start = perf_counter()
    result = function(path)

    return result, perf_counter() - start


def peak_memory(function: Callable[[Path], T], path: Path) -> int:
    tracemalloc.start()

    try:
        function(path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return peak


def experiment_streaming_vs_eager(
    sizes: tuple[int, ...] = (10_000, 100_000, 500_000),
) -> None:
    print("Experiment 2. Streaming vs eager reading of CSV")
    rows: list[list[str]] = []

    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)

        for size in sizes:
            path = directory / f"data_{size}.csv"
            generate_csv(path, valid=size)

            eager_count, eager_time = timed(consume_eager, path)
            stream_count, stream_time = timed(consume_streaming, path)
            pipeline_count, pipeline_time = timed(consume_pipeline, path)

            if not eager_count == stream_count == pipeline_count == size:
                raise RuntimeError("Variants processed different row counts")

            rows.append(
                [
                    f"{size:,}",
                    f"{eager_time:.3f}",
                    f"{stream_time:.3f}",
                    f"{peak_memory(consume_eager, path) / MEGABYTE:.2f}",
                    f"{peak_memory(consume_streaming, path) / MEGABYTE:.2f}",
                    f"{pipeline_time:.3f}",
                    f"{peak_memory(consume_pipeline, path) / MEGABYTE:.2f}",
                ]
            )

    print_table(
        [
            "Records",
            "Eager, s",
            "Streaming, s",
            "Eager peak, MB",
            "Streaming peak, MB",
            "Full pipeline, s",
            "Pipeline peak, MB",
        ],
        rows,
    )


# --------------------------------------------------- experiment 3


def experiment_chaining() -> None:
    print("Experiment 3. Exception chaining")

    with tempfile.TemporaryDirectory() as name:
        path = Path(name) / "wrong.csv"
        path.write_text(
            ",".join(HEADER) + "\nPC-001,Laptop,Lenovo,ThinkPad,wrong\n",
            encoding="utf-8",
        )
        rules = ValidationRules.from_lists(TYPES, MANUFACTURERS)

        try:
            for raw in CsvImporter().read(path):
                validate_record(raw, rules)
        except RecordValidationError as error:
            print(f"Caught: {type(error).__name__}: {error}")
            print(f"  line_number={error.line_number}, field={error.field!r}")
            cause = error.__cause__
            print(f"  __cause__: {type(cause).__name__}: {cause}")
            print("Traceback:")
            print(
                "".join(
                    traceback.format_exception(
                        type(error), error, error.__traceback__
                    )
                ).rstrip()
            )


# --------------------------------------------------- experiment 4


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def failing_records(after: int) -> Iterator[EquipmentRecord]:
    for number in range(after):
        yield EquipmentRecord(f"PC-{number + 1:03d}", "Laptop", "Dell", "XPS", 1.0)

    raise OSError("simulated disk failure")


def experiment_atomic_output() -> None:
    print("Experiment 4. Atomic output")

    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        target = directory / "result.json"
        good = [
            EquipmentRecord("PC-001", "Laptop", "Lenovo", "ThinkPad", 100.0),
            EquipmentRecord("PC-002", "Monitor", "Dell", "U2723QE", 200.0),
        ]
        JsonExporter().write(good, target)
        before = digest(target)
        print(f"Previous valid output written, sha256={before}")

        try:
            JsonExporter().write(failing_records(after=2), target)
        except DataExportError as error:
            print(f"Export failed: {type(error).__name__}: {error}")
            print(f"  cause: {type(error.__cause__).__name__}: {error.__cause__}")

        print("Previous output intact:", digest(target) == before)
        print("Temporary file removed:", not temporary_path(target).exists())

        blocked = directory / "blocked.json"
        blocked.mkdir()
        source = directory / "input.csv"
        generate_csv(source, valid=5)
        config = (
            f"input:\n  path: {source.name}\n"
            f"output:\n  path: {blocked.name}\n"
            "processing:\n  skip_invalid: true\n"
            f"  allowed_types: [{', '.join(TYPES)}]\n"
            f"  allowed_manufacturers: [{', '.join(MANUFACTURERS)}]\n"
        )
        config_path = directory / "config.yaml"
        config_path.write_text(config, encoding="utf-8")

        with redirect_stderr(io.StringIO()) as captured:
            try:
                importer_main(["--config", str(config_path)])
                code = 0
            except SystemExit as exit_info:
                code = int(str(exit_info.code))

        message = [x for x in captured.getvalue().splitlines() if "Application error" in x]
        print("main() with an output path that is a directory:")
        print(f"  exit code = {code}")
        print(f"  logged: {message[0].split(' | ')[-1] if message else '-'}")
        print("  temporary file left:", temporary_path(blocked).exists())


# --------------------------------------------------- experiment 5


@dataclass(frozen=True)
class ConfigCase:
    name: str
    content: str | None
    prepare: Callable[[Path], None] | None = None


def valid_config_text(
    input_name: str = "input.csv",
    output: str = "out/result.json",
    minimum: str = "0",
) -> str:
    return (
        f"input:\n  path: {input_name}\n"
        f"output:\n  path: {output}\n"
        f"processing:\n  skip_invalid: true\n  minimum_value: {minimum}\n"
        f"  allowed_types: [{', '.join(TYPES)}]\n"
        f"  allowed_manufacturers: [{', '.join(MANUFACTURERS)}]\n"
    )


def create_blocking_file(directory: Path) -> None:
    (directory / "file.txt").write_text("x", encoding="utf-8")


def experiment_configuration_errors() -> None:
    print("Experiment 5. Configuration errors")
    cases = [
        ConfigCase("config.yaml is missing", None),
        ConfigCase("invalid YAML", "input: [unclosed\noutput: {a: 1\n"),
        ConfigCase("no 'input' key", "output:" + valid_config_text().split("output:", 1)[1]),
        ConfigCase("minimum_value = -5", valid_config_text(minimum="-5")),
        ConfigCase("input file is missing", valid_config_text(input_name="nope.csv")),
        ConfigCase("output directory does not exist", valid_config_text(output="new/dir/result.json")),
        ConfigCase(
            "output directory is a file",
            valid_config_text(output="file.txt/result.json"),
            prepare=create_blocking_file,
        ),
    ]
    rows: list[list[str]] = []

    for case in cases:
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            generate_csv(directory / "input.csv", valid=3)
            config_path = directory / "config.yaml"

            if case.content is not None:
                config_path.write_text(case.content, encoding="utf-8")

            if case.prepare is not None:
                case.prepare(directory)

            try:
                load_and_validate(config_path)
                outcome = "valid configuration"
            except ApplicationError as error:
                outcome = f"{type(error).__name__}: {error}"

            with redirect_stderr(io.StringIO()):
                try:
                    importer_main(["--config", str(config_path)])
                    code = "0"
                except SystemExit as exit_info:
                    code = str(exit_info.code)

            rows.append([case.name, outcome.replace(name, "<dir>"), code])

    print_table(["Case", "Behaviour", "Exit"], rows)


EXPERIMENTS: dict[str, Callable[[], None]] = {
    "strict": experiment_strict_vs_tolerant,
    "streaming": experiment_streaming_vs_eager,
    "chaining": experiment_chaining,
    "atomic": experiment_atomic_output,
    "config": experiment_configuration_errors,
}


def main(argv: list[str] | None = None) -> None:
    names = argv if argv is not None else sys.argv[1:]
    selected = names or list(EXPERIMENTS)
    unknown = [n for n in selected if n not in EXPERIMENTS]

    if unknown:
        raise SystemExit(f"Unknown experiment: {unknown}. Choose from {list(EXPERIMENTS)}")

    for index, name in enumerate(selected):
        if index:
            print()

        EXPERIMENTS[name]()


if __name__ == "__main__":
    main()
