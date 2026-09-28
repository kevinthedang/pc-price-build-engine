# PC Price Build Engine

A Python project for organizing PC part data and checking basic CPU-to-motherboard compatibility. Price tracking and data collection are planned, but are not implemented yet.

## Roadmap

- [ ] Expand component catalogs and compatibility checks.
- [ ] Track dated price observations.
- [ ] Add price sources only where collection is permitted, respecting source terms and access limits.

## Current Features

- Loads CPU and motherboard catalogs from JSON files in `data/`.
- Finds motherboards matching a selected CPU's socket and a requested form factor.
- Includes basic command-line integration tests.

## Requirements

- Python 3

## Usage

From the project root, run:

```bash
python3 app/main.py --cpu-id cpu-000000002 --form-factor ATX
```

The CPU ID must exist in `data/cpus.json`. The form factor must match a value in `data/motherboards.json`, such as `ATX`, `Micro-ATX`, or `Mini-ITX`.

## Data

`data/cpus.json` contains CPU records with these fields:

- `id`: unique CPU identifier
- `name`: processor name
- `socket`: CPU socket
- `tdp`: thermal design power in watts, as an integer

`data/motherboards.json` contains motherboard records with these fields:

- `id`: unique motherboard identifier
- `name`: motherboard model
- `socket`: motherboard CPU socket
- `form_factor`: motherboard size, such as `ATX` or `Micro-ATX`

Form-factor values are currently matched exactly, including capitalization and punctuation.

## Tests

Run the test suite from the project root:

```bash
python3 -m unittest discover -s tests -v
```
