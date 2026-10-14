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

## Author

Student: Surname Name
Group: XX-00
