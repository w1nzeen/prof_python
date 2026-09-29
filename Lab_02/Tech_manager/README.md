# Tech Manager

Laboratory project for the course
"Professional Python".

## Description

Console application for managing technic.

Lab 01: project structure, virtual environment, Git.
Lab 02: data structures and functional decomposition
(variant 13 - computer equipment accounting).

## Requirements

Python 3.11+

## Installation

python -m venv .venv

Activate the virtual environment.

python -m pip install -e ".[dev]"

## Run

python -m tech_manager.main

or

tech-manager

Benchmark (list vs dict vs set):

python -m tech_manager.benchmark

Tests:

python -m pytest

## Project structure

src/tech_manager/models.py
Data model `Tech` (Lab 01).

src/tech_manager/services.py
Business logic from Lab 01.

src/tech_manager/data.py
Demo data and test data generator.

src/tech_manager/processors.py
Unique values, index, grouping, filtering, searching, sorting, pipeline.

src/tech_manager/analytics.py
Aggregation, statistics, summary export.

src/tech_manager/decorators.py
Decorators: `measure_time`, `log_operation(history)`.

src/tech_manager/benchmark.py
Performance comparison of list, dict and set.

src/tech_manager/main.py
Application entry point.

tests/
Unit tests (pytest).

## Author

Student: Bohdan Rak
Group: FEP-33
