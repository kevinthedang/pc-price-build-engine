# PC Price Build Engine

![Tests Workflow](https://github.com/kevinthedang/pc-price-build-engine/actions/workflows/tests.yml/badge.svg)

A Python project for organizing PC part data, matching motherboards to CPUs, and screening PSUs by estimated wattage. The build engine also accepts a required storage drive and memory kit so the generated report reflects the actual selected parts.

## Roadmap

- [ ] Expand component catalogs and compatibility checks.
- [ ] Track dated price observations.
- [ ] Add price sources only where collection is permitted, respecting source terms and access limits.

## Current Features

- Loads CPU, GPU, storage, memory, motherboard, case, cooler, and PSU catalogs from JSON seed files in `data/`.
- Finds motherboards matching a selected CPU's socket, selected memory type, and optional form factor.
- Finds cases that support a matching motherboard form factor and the selected GPU's length.
- Lists PSUs that meet a basic estimated wattage requirement for the selected CPU and GPU.
- Reports selected parts and an estimated cost breakdown using the lowest matching offer for each priced component.
- Accepts and displays `cheapest`, `budget`, `balanced`, `premium`, and `top_of_line` pricing modes, plus an optional `--budget-limit`; these options do not currently rerank complete builds.
- Includes basic command-line integration tests.

## Requirements

- Python 3
- SQLite (included with Python)

## Project Structure

- `backend/`: Python build engine, CLI, and FastAPI health endpoint.
- `frontend/`: SvelteKit web client.
- `database/core/`: shared product, retailer, offer, and compatibility relationship tables.
- `database/specs/`: component-specific specification tables; apply SQL files from both folders in numeric filename order.
- `data/`: current JSON catalogs, retained as seed/import sources. The CLI still reads these files; database loading and runtime queries have not been implemented yet.

Local SQLite database files are generated artifacts and should not be committed.

## Run the API

From the project root, create and activate a virtual environment, then install the backend dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Debian or Ubuntu, if virtual environment creation reports that `ensurepip` is unavailable, install the venv package matching your Python version (for example, `sudo apt install python3.12-venv`) and retry.

Start the development server from the `backend/` directory:

```bash
python -m uvicorn api:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/api/health`, the interactive API documentation at `http://127.0.0.1:8000/docs`, and the component catalogs and build-generation endpoint are available at:

- `GET /api/catalogs`: list available catalogs and their record counts.
- `GET /api/catalogs/cpus`, `/gpus`, `/storage`, `/memory`, `/motherboards`, `/cases`, `/coolers`, and `/psus`: retrieve catalog records.
- `GET /api/builds/options?cpu_id=...&form_factor=...&memory_id=...`: return memory and motherboard-form-factor options with compatibility status and reasons. Omit selections that have not been made yet.
- `POST /api/builds/generate`: generate a compatible build from selected component IDs.

For example:

```bash
curl -X POST http://127.0.0.1:8000/api/builds/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "cpu_id": "cpu-000000002",
    "gpu_id": "gpu-000000001",
    "storage_ids": ["storage-000000001", "storage-000000003"],
    "memory_id": "memory-000000003",
    "form_factor": "ATX",
    "mode": "budget",
    "budget_limit_cents": 150000
  }'
```

Use `storage_ids` to include multiple drives. Each selected ID is included and priced; unselected storage rows are omitted by the frontend. The singular `storage_id` field remains supported for existing clients, but provide one field or the other, not both.

The response includes selected parts, compatible motherboard/case/PSU/cooler options, a `compatibility_checks` list with `pass`, `warning`, `fail`, `blocked`, or `unknown` statuses and user-readable reasons, the report text, and estimated pricing in integer cents. A build is marked `compatible: false` when a modeled compatibility check fails. `warning` checks do not make a build incompatible but flag a risk worth reviewing; for example, the `memory_speed` check warns when the selected memory's speed is above the CPU's rated maximum for that memory type (running it there relies on an XMP/EXPO overclock). Warnings are also listed under `Compatibility:` in the report text. `blocked` checks depend on an upstream fit check; `unknown` means the catalog does not contain enough data to verify that rule. Storage-interface compatibility is currently `unknown` because storage connector and motherboard slot specifications are not modeled. `form_factor` and `budget_limit_cents` are optional; `mode` accepts `cheapest`, `budget`, `balanced`, `premium`, or `top_of_line`. Pricing modes are currently reported but do not rerank complete builds. The frontend uses the options endpoint to hide incompatible memory and form factors by default; “Show incompatible options” reveals them with explanations. The generation endpoint remains authoritative and returns the same detailed checks. The frontend's Vite development server proxies `/api` requests to `http://127.0.0.1:8000`.

## Currency conversion

The API and catalog prices remain USD. The frontend can display estimated totals and component costs in USD, CAD, EUR, GBP, AUD, and JPY. It loads daily reference rates from the no-key [Frankfurter API](https://frankfurter.dev/), shows the returned rate date, and converts a budget back to USD before submitting it to the build API. If rate loading fails, the UI reports the error and keeps USD available. Converted amounts are estimates, not retailer quotes; they do not include local taxes, import charges, or retailer/payment-provider exchange fees.

When the frontend and API are hosted on different origins, set `VITE_API_BASE_URL` to the API origin when building the frontend. For a FastAPI server hosted outside Cloudflare Workers, set `PC_BUILD_ALLOWED_ORIGINS` on the API to the frontend origin (or comma-separated list of allowed frontend origins); the Worker deployment below has its own CORS configuration.

## Deploy the API to Cloudflare Workers

The API can run as a Python Worker using Cloudflare's ASGI adapter for FastAPI. The Worker loads the JSON files from `data/` through a static-assets binding, so the catalogs and offers remain the same source files used by local development. Cloudflare Python Workers require Python 3.13 or newer, `uv`, and Node.js.

From the repository root, install the Worker dependencies and start a local Cloudflare Worker:

```bash
uv sync
uv run pywrangler dev
```

Authenticate Wrangler with your Cloudflare account, then deploy:

```bash
uv run pywrangler login
uv run pywrangler deploy
```

The deployed API's `*.workers.dev` URL can be used initially; optionally configure a custom domain for a stable API URL. In the Cloudflare Pages project settings, set `VITE_API_BASE_URL` to that API origin for both production and preview builds, then trigger a new Pages deployment. The Worker allows cross-origin requests without credentials; its API endpoints are public and do not use cookie-based authentication. Local API runs continue to use `PC_BUILD_ALLOWED_ORIGINS` for origin restrictions.

### Automatically deploy from GitHub Actions

The Tests workflow runs the unit tests on pull requests to `master`. The separate Deploy API workflow reuses that test job on pushes to `master` and deploys the Worker only after tests pass. Pull requests run tests only; they do not deploy.

To enable deployment, create a Cloudflare API token with permission to edit Workers scripts, scoped to the Cloudflare account that should host the Worker. In GitHub, open **Settings > Environments > production** and add these environment secrets:

- `CLOUDFLARE_API_TOKEN`: the token value.
- `CLOUDFLARE_ACCOUNT_ID`: the Cloudflare account ID where the Worker is deployed.

The configured Worker name is `pc-price-build-engine-api` in `wrangler.jsonc`; do not create a secret with that name. If deployment reports “No access to the specified service,” verify that the `production` environment token has Workers Scripts edit permission for the account selected by `CLOUDFLARE_ACCOUNT_ID`, and that the account ID is copied from that same Cloudflare account. A token can authenticate successfully but still lack permission to edit that Worker service.

Do not put the token in the repository or in Wrangler configuration. Once these environment secrets are set, merging or pushing to `master` will run tests and then deploy the Worker automatically.

## Run the Frontend

In a separate terminal, install the frontend dependencies and start the SvelteKit development server:

```bash
cd frontend
npm ci
npm run dev -- --open
```

Vite prints the local URL, usually `http://localhost:5173`. Keep the API server running in its own terminal. The frontend loads the component catalogs and submits builds through the API.

For Cloudflare Pages, set the project root directory to `frontend`, set the `NODE_VERSION` environment variable to `24.21.0`, and set `VITE_API_BASE_URL` to the deployed API origin for production and preview builds. For an API hosted outside Cloudflare Workers, configure `PC_BUILD_ALLOWED_ORIGINS` with the corresponding Pages origin. The `frontend/.nvmrc` file pins the Node.js version for local Node version managers.

## Usage

From the project root, run:

```bash
python3 backend/main.py --cpu-id cpu-000000002 --gpu-id gpu-000000001 --storage-id storage-000000001 --memory-id memory-000000003 --form-factor ATX
```

> [!NOTE]
> The CPU, GPU, storage, and memory IDs must exist in `data/cpus.json`, `data/gpus.json`, `data/storage.json`, and `data/memory.json`. The selected GPU is required and displayed in the report, while motherboard compatibility checks also require a matching CPU socket, compatible memory type, and optional form factor. `--cpu`, `--gpu`, `--storage`, and `--memory` are accepted aliases for the corresponding `--*-id` arguments. To list all motherboards that match the CPU and memory type, omit `--form-factor`:

Example AM4 DDR4 system with shorter syntax:

```bash
python3 backend/main.py --cpu cpu-000000002 --gpu gpu-000000001 --storage storage-000000001 --memory memory-000000003
```

When provided, the form factor must exactly match a value in `data/motherboards.json`, such as `ATX`, `Micro-ATX`, or `Mini-ITX`.

> [!NOTE]
> PSU filtering uses the greater of the estimated system requirement (CPU TDP + GPU TDP + 200 W for the rest of the system) and the selected GPU's manufacturer-recommended minimum PSU wattage, when available. This is only a screening heuristic, not a guarantee of compatibility or safety; check the component and PSU manufacturers' recommendations. The efficiency label is displayed but does not determine PSU quality or wattage compatibility.

## Data

`data/cpus.json` contains CPU records with these fields:

- `id`: unique CPU identifier
- `name`: processor name
- `socket`: CPU socket
- `core_count` and `thread_count`: total physical cores and logical threads
- `performance_core_count` and `efficiency_core_count`: optional P-core/E-core breakdown for hybrid CPUs
- `base_clock_mhz` and `max_clock_mhz`: advertised base and maximum boost/turbo clock speeds
- `efficiency_core_base_clock_mhz`: optional base clock for E-cores on hybrid CPUs
- `max_clock_type`: whether the maximum clock is advertised as `Max boost` or `Max turbo`
- `max_pcie_standard`: highest PCIe generation supported by the CPU, such as `PCIe 3.0` or `PCIe 5.0`
- `max_memory_speeds`: manufacturer-rated maximum memory speed for each supported memory type, as a list of `memory_type` and `max_speed_mhz` entries (CPUs that support both DDR4 and DDR5 list both)
- `tdp`: thermal design power in watts, as an integer
- `stock_cooler_included`: whether the standard boxed CPU includes a stock cooler

`data/motherboards.json` contains motherboard records with these fields:

- `id`: unique motherboard identifier
- `name`: motherboard model
- `socket`: motherboard CPU socket
- `form_factor`: motherboard size, such as `ATX` or `Micro-ATX`
- `memory_type`: supported memory generation, such as `DDR4` or `DDR5`
- `memory_slots`: physical DIMM slots available on the board
- `max_memory_gb`: total supported system memory in GB
- `wifi`: whether the board includes integrated Wi-Fi

`data/storage.json` contains storage records with these fields:

- `id`: unique storage identifier
- `name`: storage name
- `type`: storage type (`SATA SSD`, `NVMe SSD`, `SATA HDD`, etc.)
- `size_gb`: amount of gigabytes of storage
- `pcie_compatibility`: list of PCIe compatibility strings, such as `PCIe 4.0 x4`

`data/memory.json` contains memory records with these fields:

- `id`: unique memory identifier
- `name`: memory kit name
- `memory_type`: memory generation, such as `DDR4` or `DDR5`
- `capacity_gb`: amount of gigabytes per module
- `modules`: number of modules in the kit
- `speed_mhz`: rated memory speed in MHz

`data/gpus.json` contains GPU records with these fields:

- `id`: unique GPU identifier
- `name`: graphics card model
- `vram`: video memory in GB, as an integer
- `tdp`: graphics card power in watts, as an integer
- `length_mm`: exact card variant length in millimeters
- `game_clock_mhz` and `boost_clock_mhz`: optional manufacturer-advertised game and boost clocks
- `oc_game_clock_mhz` and `oc_boost_clock_mhz`: optional overclocked-mode game and boost clocks
- `pcie_standard`: optional PCIe generation, such as `PCIe 5.0`
- `recommended_psu_w`: optional manufacturer-recommended minimum system PSU wattage
- `pcie_slot_width`: optional physical card thickness in slot widths, including fractional values
- `display_outputs`: optional list of display connectors, each with a `type`, optional `version`, and `count`

> [!NOTE]
> GPU entries are specific partner-card variants because physical length differs across cards using the same GPU chip.

`data/cases.json` contains case records with these fields:

- `id`: unique case identifier, also used as `product_id` by case offers in `data/offers.json`
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

- `id`: unique cooler identifier
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

`data/offers.json` contains retailer offers for components. Each offer identifies a component using `component_type` and `product_id`; the product ID must match the component's `id` in its catalog. Offers include retailer, price, shipping, currency, availability, condition, seller, and the time the offer was checked. The report uses the lowest price-plus-shipping offer when available; components without a matching offer contribute `$0.00` to the estimate. Prices are estimates and may be stale.

The SQLite schema is normalized: each JSON component's `id` and `name` are stored once in `products`, while component-specific fields are stored in the corresponding specs table using `product_id`. For example, a PSU's `id` and `name` go into `products`, and its `wattage` and `efficiency` go into `psu_specs`. CPU-specific fields, including core/thread counts, advertised clock speeds, and maximum supported PCIe generation, are defined in `cpu_specs`; rated maximum memory speeds are stored as one row per CPU and memory type in `cpu_memory_speeds`; optional GPU clocks, PCIe generation, manufacturer PSU recommendation, and physical slot width are defined in `gpu_specs`. GPU display connectors are stored as one row per connector type/version in `gpu_display_outputs`. Offers reference the shared product row. Offer prices and shipping are stored as integer cents. Apply SQL files from both `database/core/` and `database/specs/` in numeric filename order, and enable SQLite foreign-key enforcement on each connection. The schema tests validate the DDL and ensure each source catalog has product IDs and names. The database is schema-only at present: catalogs remain JSON seed files, and database loading and runtime queries have not been implemented.

GPU dimensions and case clearances are based on manufacturer specifications: [Gigabyte RTX 4060](https://www.gigabyte.com/Graphics-Card/GV-N4060WF2OC-8GD/sp), [RTX 4070 SUPER](https://www.gigabyte.com/Graphics-Card/GV-N407SWF3OC-12GD-rev-10/sp), [RTX 4080 SUPER](https://www.gigabyte.com/Graphics-Card/GV-N408SGAMING-OC-16GD/sp), [RTX 4090](https://www.gigabyte.com/Graphics-Card/GV-N4090WF3V2-24GD-rev-10-11/sp), [SAPPHIRE RX 7600](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7600-8g-gddr6), [RX 7800 XT](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7800-xt-16g-gddr6), [RX 7900 XTX](https://www.sapphiretech.com/en/consumer/pulse-radeon-rx-7900-xtx-24g-gddr6), and [ASUS Prime RX 9070 XT OC Edition specifications](https://www.asus.com/us/motherboards-components/graphics-cards/prime/prime-rx9070xt-o16g/techspec/). The ASUS catalog entry records its advertised default and OC-mode clocks, PCIe 5.0 interface, 750 W PSU recommendation, and 2.5-slot thickness. Case references: [Corsair 4000D Airflow](https://www.corsair.com/us/en/p/pc-cases/cc-9011200-ww/4000d-airflow-tempered-glass-mid-tower-atx-case-black-cc-9011200-ww), [Cooler Master NR200P](https://www.coolermaster.com/en-global/products/masterbox-nr200p/), [Lian Li A3-mATX](https://lian-li.com/product/a3-matx/), and [Fractal Design Pop Mini Air](https://www.fractal-design.com/products/cases/pop-series/pop-mini-air/pop-mini-air-rgb-black-tg-clear-tint/).

Cooler socket and dimension data is based on [Thermalright Peerless Assassin 120 SE](https://www.thermalright.com/product/peerless-assassin-120-se/), [Frozen Notte 240](https://www.thermalright.com/product/frozen-notte-240-black-argb/), and [Frozen Notte 360](https://www.thermalright.com/product/frozen-notte-360-black-argb/) manufacturer specifications. The stock-cooler flags assume boxed retail CPU versions; Intel tray/bulk CPUs may differ.

Case matching currently checks motherboard form factor and GPU length only. GPU thickness, front-mounted radiators, and other layout constraints can further reduce clearance.

Form-factor values are currently matched exactly, including capitalization and punctuation.

## Tests

Run the test suite from the project root:

```bash
python3 -m unittest discover -s tests -v
```
