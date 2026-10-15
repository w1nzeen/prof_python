"""Assembling the lazy pipeline from separate stages.

Input file -> read_lines -> clean_lines -> parse_csv_rows
-> validate_devices -> normalize_devices -> filters -> consumer
"""

import logging
from collections.abc import Generator, Iterable, Iterator
from itertools import chain
from pathlib import Path

from equipment_manager.models import Device
from equipment_manager.streaming.filters import (
    ValidationStats,
    filter_by_manufacturer,
    filter_by_type,
    validate_devices,
)
from equipment_manager.streaming.parsers import clean_lines, parse_csv_rows
from equipment_manager.streaming.readers import read_lines
from equipment_manager.streaming.transformations import normalize_devices

logger = logging.getLogger(__name__)


def log_stage(
    name: str,
    devices: Iterable[Device],
) -> Generator[Device, None, None]:
    """Pass-through stage that logs how many records went through.

    `finally` also runs when the consumer stops early (generator close).
    """
    count = 0

    try:
        for device in devices:
            count += 1
            yield device
    finally:
        logger.debug("stage '%s': %d record(s) passed", name, count)


def build_pipeline(
    path: Path,
    *,
    manufacturer: str | None = None,
    device_type: str | None = None,
    stats: ValidationStats | None = None,
    log_stages: bool = False,
) -> Generator[Device, None, None]:
    """Build a lazy pipeline: nothing is read until it is consumed."""
    lines = read_lines(path)
    cleaned = clean_lines(lines)
    rows = parse_csv_rows(cleaned)
    valid = validate_devices(rows, stats)
    stream: Generator[Device, None, None] = normalize_devices(valid)

    if log_stages:
        stream = log_stage("validated", stream)

    if manufacturer is not None:
        stream = filter_by_manufacturer(stream, manufacturer)

    if device_type is not None:
        stream = filter_by_type(stream, device_type)

    if log_stages:
        stream = log_stage("filtered", stream)

    return stream


def build_multi_file_pipeline(
    paths: Iterable[Path],
    *,
    manufacturer: str | None = None,
    device_type: str | None = None,
    stats: ValidationStats | None = None,
) -> Iterator[Device]:
    """One stream from several files (itertools.chain.from_iterable)."""
    return chain.from_iterable(
        build_pipeline(
            path,
            manufacturer=manufacturer,
            device_type=device_type,
            stats=stats,
        )
        for path in paths
    )
