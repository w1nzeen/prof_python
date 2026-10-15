# Equipment Manager

Laboratory project for the course "Professional Python".
Variant 13: computer equipment accounting system.

## Description

Console application for managing computer equipment.
Each device has an inventory number, type, manufacturer, model and cost.

Features:

- search devices;
- filter devices by manufacturer;
- average cost of devices;
- the most expensive device;
- total cost of all equipment;
- menu-driven interface with input validation.

## Requirements

Python 3.11+

## Installation

```
python -m venv .venv
```

Activate the virtual environment:

- Windows: `.venv\Scripts\activate`
- Linux/macOS: `source .venv/bin/activate`

```
python -m pip install -e ".[dev]"
```

## Run

Interactive menu:

```
python -m equipment_manager.main
```

or

```
equipment-manager
```

Demo mode of laboratory work 1 (no input required):

```
python -m equipment_manager.main --demo
```

Laboratory work 3 (streaming pipeline, run from the project root):

```
python -m equipment_manager.main --stream              # demo on data/input.csv
python -m equipment_manager.main --stream -v           # + log of pipeline stages
python -m equipment_manager.main --generate 100000     # create data/large.csv
python -m equipment_manager.main --stream --path data/large.csv
python -m equipment_manager.main --experiment          # eager vs lazy (takes ~1-2 min)
python -m equipment_manager.main --experiment --sizes 10000 100000
```

Laboratory work 2 (data processing) and benchmark:

```
python -m equipment_manager.main --analysis
python -m equipment_manager.main --benchmark
```

Example output:

```
Statistics:
Devices count: 6
Average cost: 18633.42
Total cost: 111800.50
Most expensive device: Dell Latitude 5440 (36900.00)
```

## Tests

```
python -m pytest
```

## Project structure

```
src/equipment_manager/models.py      Data model (Device dataclass)
src/equipment_manager/services.py    Business logic (lab 1)
src/equipment_manager/exceptions.py  Custom exceptions
src/equipment_manager/data.py        Sample data, tuples, data generator (lab 2)
src/equipment_manager/processors.py  Filtering, grouping, indexing (lab 2)
src/equipment_manager/analytics.py   Aggregation, sorting, closures (lab 2)
src/equipment_manager/decorators.py  measure_time, record_operation (lab 2)
src/equipment_manager/benchmark.py   list vs dict benchmark (lab 2)
src/equipment_manager/main.py        Application entry point
src/equipment_manager/streaming/     Streaming pipeline (lab 3)
data/input.csv                       Sample input for lab 3
reports/                             Reports in .docx format
tests/                               Unit tests
```

## Laboratory work 2: data structures

| Structure / feature | Where it is used |
| --- | --- |
| list | `DEVICES`, results of filters and sorting |
| tuple | `DEVICE_TYPES`, `MANUFACTURERS`, `calculate_cost_range()` -> `(min, max)` |
| set | `get_unique_manufacturers()`, `get_unique_types()` |
| dict | `create_device_index()`, `calculate_cost_by_manufacturer()` |
| Counter | `count_by_type()` |
| defaultdict | `group_by()` |
| deque | `OPERATION_HISTORY` (last 5 operations) |
| list / set / dict comprehension | `filter_by_manufacturer()` / `get_unique_manufacturers()` / `create_device_index()` |
| generator expression | `calculate_total_cost()` |
| `*args` / `**kwargs` | `calculate_average_values()` / `create_device()` |
| lambda | sorting keys, `max(..., key=...)`, pipeline steps |
| closure | `create_cost_filter()`, `create_manufacturer_filter()` |
| decorators | `measure_time`, parameterized `record_operation(history)` |

Additional features: universal filter (`filter_items`), universal sorting
(`sort_devices`), parameterized decorator, closure filters, nested grouping,
Counter statistics, deque history, benchmark, pipeline (`process_pipeline`).

### Complexity of operations

| Operation | Code | Complexity |
| --- | --- | --- |
| Search in list | `find_linear()` | O(n) |
| Build dict index | `create_device_index()` | O(n) |
| Search in dict index | `index.get(number)` | O(1) on average |
| Membership in set | `manufacturer in manufacturers` | O(1) on average |
| Sorting | `sort_by_cost()` | O(n log n) |
| Grouping | `group_by()` | O(n) |

### Benchmark (search for the last device, average of 100 runs)

| Records | list search, s | dict search, s |
| --- | --- | --- |
| 1 000 | 0.0000255 | 0.0000001 |
| 10 000 | 0.0003923 | 0.0000001 |
| 100 000 | 0.0040433 | 0.0000001 |

The list search time grows about 10 times when the data grows 10 times
(O(n)), while the dict search time stays almost constant (O(1)).
Results depend on the computer; run `--benchmark` to get your own numbers.

## Laboratory work 3: iterators, generators, streaming

Input format: `inventory_number,type,manufacturer,model,cost`.

Pipeline: `read_lines` -> `clean_lines` -> `parse_csv_rows` -> `validate_devices`
-> `normalize_devices` -> filters -> consumer (aggregation, batching, search).

| Module (`streaming/`) | Content |
| --- | --- |
| `iterators.py` | custom iterable/iterator classes, infinite generator, recursive `flatten` (`yield from`) |
| `readers.py`, `parsers.py` | streaming reading, cleaning, CSV parsing |
| `filters.py` | validation with invalid counter, filters, lazy search (`find_first`) |
| `transformations.py` | normalization, `accumulate`, `pairwise`, `tee` |
| `batches.py` | `batched` (`islice`), `dynamic_batches` |
| `analytics.py` | single-pass statistics, `Counter`, `groupby` |
| `pipeline.py` | assembling the pipeline, `chain` for several files, stage logging |
| `experiment.py` | data generator, eager vs lazy time/memory, early termination |

Experiment results (Python 3.12, Linux; your numbers will differ):

| Records | Eager, s | Lazy, s | Eager peak, MB | Lazy peak, MB |
| --- | --- | --- | --- | --- |
| 10 000 | 0.096 | 0.090 | 8.26 | 0.04 |
| 100 000 | 1.083 | 0.830 | 82.39 | 0.05 |
| 500 000 | 5.286 | 4.307 | 412.63 | 0.05 |

Lazy processing keeps memory almost constant and returns the first record
immediately; the difference in total time is small, so a generator is not
"always faster", its main advantage is memory and early termination.

## Author

Student: Surname Name
Group: XX-00
