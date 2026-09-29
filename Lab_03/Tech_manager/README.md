# Tech Manager

Laboratory project for the course
"Professional Python".

## Description

Console application for managing technic.

Lab 01: project structure, virtual environment, Git.
Lab 02: data structures and functional decomposition
(variant 13 - computer equipment accounting).
Lab 03: iterators, generators and streaming data processing
(variant 13 - streaming processing of computer equipment records).

## Requirements

Python 3.11+

## Installation

python -m venv .venv

Activate the virtual environment.

python -m pip install -e ".[dev]"

## Run

Lab 01 / Lab 02:

python -m tech_manager.main

or

tech-manager

Benchmark (list vs dict vs set):

python -m tech_manager.benchmark

Lab 03 - streaming pipeline demo (data/input.csv):

python -m tech_manager.streaming.main

or

tech-manager-stream

Lab 03 - eager vs lazy experiment (10k / 100k / 500k / 1M records):

python -m tech_manager.streaming.experiment

or

tech-manager-experiment

Tests:

python -m pytest

## Project structure

src/tech_manager/models.py
Data model `Tech` (Lab 01).

src/tech_manager/services.py
Business logic from Lab 01.

src/tech_manager/data.py, processors.py, analytics.py, decorators.py, benchmark.py
Lab 02: data structures, grouping, filtering, aggregation, decorators, benchmark.

src/tech_manager/streaming/
Lab 03: lazy streaming pipeline.

    records.py          NamedTuple `TechRecord` (bridge to `Tech`).
    iterators.py        Custom iterator classes (iterable + iterator).
    generators.py       Generator functions: yield, yield from, infinite, recursive.
    readers.py          Source stage: read_lines, clean_lines.
    parsers.py          Parsing stage: CSV rows.
    filters.py          Validation (with valid/invalid report) and filtering.
    transformations.py  Normalization, conversion to `Tech`.
    batches.py          Fixed-size and dynamic batching.
    analytics.py        Streaming aggregation, accumulate, pairwise, groupby.
    search.py           Lazy search with early termination.
    pipeline.py         Pipeline assembly, stage counters/logging, export sink.
    datagen.py          Large test file generator.
    eager.py            Eager implementation (for comparison).
    experiment.py       Time / peak memory / time-to-first-result experiment.
    main.py             Demonstration.

data/input.csv, data/input_part2.csv
Demo input files (with deliberately invalid rows).

tests/
Unit tests (pytest).

## Author

Student: Bohdan Rak
Group: FEP-33
