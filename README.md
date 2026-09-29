# PC Price Build Engine

A Python project for organizing PC part data, matching motherboards to CPUs, and screening PSUs by estimated wattage. Price tracking and data collection are planned, but are not implemented yet.

## Roadmap

- [ ] Expand component catalogs and compatibility checks.
- [ ] Track dated price observations.
- [ ] Add price sources only where collection is permitted, respecting source terms and access limits.

## Current Features

- Loads CPU, GPU, storage, motherboard, case, and PSU catalogs from JSON files in `data/`.
- Finds motherboards matching a selected CPU's socket, optionally filtered by form factor.
- Finds cases that support a matching motherboard form factor and the selected GPU's length.
- Lists PSUs that meet a basic estimated wattage requirement for the selected CPU and GPU.
- Includes basic command-line integration tests.

## Requirements

- Python 3

## Usage

From the project root, run:

```bash
python3 app/main.py --cpu-id cpu-000000002 --gpu-id gpu-000000001 --storage-id storage-000000002 --form-factor ATX
```

> [!NOTE]
> The CPU, GPU, and Storage IDs must exist in `data/cpus.json`, `data/gpus.json`, `data/storage.json`. The selected GPU is required and shown in the results, but motherboard matching still uses the CPU socket and optional form factor. `--gpu` is also accepted as an alias for `--gpu-id`. Same thing with `--cpu` and `--storage` To list all motherboards with a compatible socket, omit `--form-factor`:

```bash
python3 app/main.py --cpu cpu-000000002 --gpu gpu-000000001 --storage storage-000000002
```

When provided, the form factor must exactly match a value in `data/motherboards.json`, such as `ATX`, `Micro-ATX`, or `Mini-ITX`.

> [!NOTE]
> PSU filtering uses a rough minimum-wattage estimate: CPU TDP + GPU TDP + 200 W for the rest of the system. This is only a screening heuristic, not a guarantee of compatibility or safety; check the component and PSU manufacturers' recommendations. The efficiency label is displayed but does not determine PSU quality or wattage compatibility.

## Data

`data/cpus.json` contains CPU records with these fields:

- `id`: unique CPU identifier
- `name`: processor name
- `socket`: CPU socket
- `tdp`: thermal design power in watts, as an integer
- `stock_cooler_included`: whether the standard boxed CPU includes a stock cooler

`data/motherboards.json` contains motherboard records with these fields:

- `id`: unique motherboard identifier
- `name`: motherboard model
- `socket`: motherboard CPU socket
- `form_factor`: motherboard size, such as `ATX` or `Micro-ATX`

`data/storage.json` contains storage records with these fields:

- `id`: unique storage identifier
- `name`: storage name
- `type`: storage type (`SATA SSD`, `NVMe SSD`, `SATA HDD`, etc.)
- `size_gb`: amount of gigabytes of storage
- `pcie_compatibility`: PCIe compatible generation

`data/gpus.json` contains GPU records with these fields:

- `id`: unique GPU identifier
- `name`: graphics card model
- `vram`: video memory in GB, as an integer
- `tdp`: graphics card power in watts, as an integer
- `length_mm`: exact card variant length in millimeters

> [!NOTE]
> GPU entries are specific partner-card variants because physical length differs across cards using the same GPU chip.

`data/cases.json` contains case records with these fields:

- `name`: case model
- `supported_motherboard_form_factors`: list of motherboard form factors supported by the case
- `max_gpu_length_mm`: maximum GPU length in millimeters
- `included_fans`: number of included fans
- `max_fans`: maximum number of fans the case supports
- `max_cpu_cooler_height_mm`: maximum air-cooler height in millimeters
- `supported_radiator_sizes_mm`: supported AIO radiator lengths in millimeters

> [!NOTE]
> Case results show the additional fans needed to fill all supported fan positions (`max_fans - included_fans`). This is a full-capacity count, not a recommendation that every position must be populated.

`data/coolers.json` contains cooler records with these fields:

- `name`: cooler model
- `type`: `air` or `aio`
- `supported_sockets`: CPU sockets supported by the cooler
- `height_mm`: air-cooler height; `null` for AIOs
- `max_tdp_w`: rough advertised cooling-capacity estimate in watts
- `radiator_size_mm`: AIO radiator length; `null` for air coolers
- `radiator_thickness_mm`: radiator thickness; `null` for air coolers
- `pump_height_mm`: AIO pump height; `null` for air coolers

> [!NOTE]
> Cooler results are filtered by CPU socket and CPU TDP, then by the selected case's air-cooler height or supported AIO radiator sizes. Maximum cooler TDP is not standardized and should be treated as a rough screening estimate, not a compatibility guarantee. AIO radiator thickness and placement constraints are recorded only partially and are not yet checked.

`data/psus.json` contains PSU records with these fields:

- `id`: unique PSU identifier
- `name`: PSU model and revision
- `wattage`: rated output in watts, as an integer
- `efficiency`: efficiency class, such as `Bronze`, `Gold`, or `Platinum`

GPU dimensions and case clearances are based on manufacturer specifications: [Gigabyte RTX 4060](https://www.gigabyte.com/Graphics-Card/GV-N4060WF2OC-8GD/sp), [RTX 4070 SUPER](https://www.gigabyte.com/Graphics-Card/GV-N407SWF3OC-12GD-rev-10/sp), [RTX 4080 SUPER](https://www.gigabyte.com/Graphics-Card/GV-N408SGAMING-OC-16GD/sp), [RTX 4090](https://www.gigabyte.com/Graphics-Card/GV-N4090WF3V2-24GD-rev-10-11/sp), [SAPPHIRE RX 7600](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7600-8g-gddr6), [RX 7800 XT](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7800-xt-16g-gddr6), [RX 7900 XTX](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7900-xtx-24g-gddr6), [Corsair 4000D Airflow](https://www.corsair.com/us/en/p/pc-cases/cc-9011200-ww/4000d-airflow-tempered-glass-mid-tower-atx-case-black-cc-9011200-ww), [Cooler Master NR200P](https://www.coolermaster.com/en-global/products/masterbox-nr200p/), [Lian Li A3-mATX](https://lian-li.com/product/a3-matx/), and [Fractal Design Pop Mini Air](https://www.fractal-design.com/products/cases/pop-series/pop-mini-air/pop-mini-air-rgb-black-tg-clear-tint/).

Cooler socket and dimension data is based on [Thermalright Peerless Assassin 120 SE](https://www.thermalright.com/product/peerless-assassin-120-se/), [Frozen Notte 240](https://www.thermalright.com/product/frozen-notte-240-black-argb/), and [Frozen Notte 360](https://www.thermalright.com/product/frozen-notte-360-black-argb/) manufacturer specifications. The stock-cooler flags assume boxed retail CPU versions; Intel tray/bulk CPUs may differ.

Case matching currently checks motherboard form factor and GPU length only. GPU thickness, front-mounted radiators, and other layout constraints can further reduce clearance.

Form-factor values are currently matched exactly, including capitalization and punctuation.

## Tests

Run the test suite from the project root:

```bash
python3 -m unittest discover -s tests -v
```
