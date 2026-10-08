import argparse
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PSU_SYSTEM_ALLOWANCE_W = 200
MEMORY_SPEEDS_MHZ = {
	"DDR4": (2133, 2400, 2666, 2800, 2933, 3000, 3200, 3466, 3600, 3733, 3800, 4000),
	"DDR5": (4800, 5200, 5600, 6000, 6200, 6400, 6800, 7000, 7200, 7600, 7800, 8000),
}
MEMORY_MODULE_CAPACITIES_GB = {
	"DDR4": (4, 8, 16, 32),
	"DDR5": (8, 12, 16, 18, 24, 32, 48, 64),
}
MAX_MEMORY_MODULE_COUNT = 4
_worker_catalogs: dict[str, str] | None = None


def load_json(filename):
	if _worker_catalogs is not None:
		try:
			return json.loads(_worker_catalogs[filename])
		except KeyError as error:
			raise FileNotFoundError(filename) from error
	with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
		return json.load(data_file)


def set_worker_catalogs(catalogs: dict[str, str]) -> None:
	global _worker_catalogs
	_worker_catalogs = catalogs


def load_offers():
	try:
		return load_json("offers.json")
	except FileNotFoundError:
		return []


def best_offer_for_product(offers, component_type, product_id):
	matching_offers = [
		offer
		for offer in offers
		if offer.get("component_type") == component_type
		and offer.get("product_id") == product_id
	]
	if not matching_offers:
		return None
	return min(
		matching_offers,
		key=lambda offer: (
			float(offer.get("price", 0.0)) + float(offer.get("shipping", 0.0)),
			offer.get("retailer", ""),
		),
	)


def offer_total(offers, component_type, product_id):
	offer = best_offer_for_product(offers, component_type, product_id)
	if offer is None:
		return 0.0
	return float(offer.get("price", 0.0)) + float(offer.get("shipping", 0.0))


def offer_total_for_component(component_type, product_id, offers):
	return offer_total(offers, component_type, product_id)


def cooler_fits_case(cooler, cpu, case):
	if cpu["socket"] not in cooler["supported_sockets"]:
		return False
	if cooler["max_tdp_w"] < cpu["tdp"]:
		return False
	if cooler["type"] == "air":
		return cooler["height_mm"] <= case["max_cpu_cooler_height_mm"]
	if cooler["type"] == "aio":
		return cooler["radiator_size_mm"] in case["supported_radiator_sizes_mm"]
	return False


def memory_profile_fits_board(
	board, memory_type, capacity_gb, module_count
):
	return (
		board["memory_type"] == memory_type
		and capacity_gb <= board["max_memory_gb"]
		and module_count <= board["memory_slots"]
	)


def available_memory_profile_shapes():
	return sorted(
		(
			memory_type,
			module_capacity_gb * module_count,
			module_count,
		)
		for memory_type, module_capacities in MEMORY_MODULE_CAPACITIES_GB.items()
		for module_capacity_gb in module_capacities
		for module_count in range(1, MAX_MEMORY_MODULE_COUNT + 1)
	)


def get_build_options(
	cpu_id=None,
	form_factor=None,
	memory_id=None,
	memory_type=None,
	memory_capacity_gb=None,
	memory_module_count=None,
	memory_speed_mhz=None,
):
	cpus = load_json("cpus.json")
	motherboards = load_json("motherboards.json")
	memory_modules = load_json("memory.json")
	offers = load_offers()
	profile_parameters = (
		memory_type,
		memory_capacity_gb,
		memory_module_count,
		memory_speed_mhz,
	)
	if any(value is not None for value in profile_parameters) and not all(
		value is not None for value in profile_parameters[:3]
	):
		raise ValueError(
			"Memory profiles require a type, total capacity, and module count."
		)
	if memory_id is not None and any(
		value is not None for value in profile_parameters
	):
		raise ValueError("Choose either a memory item or a memory profile, not both.")

	memory_profile_shapes = available_memory_profile_shapes()
	selected_profile = None
	if memory_type is not None:
		selected_profile = (
			memory_type,
			memory_capacity_gb,
			memory_module_count,
		)
		if selected_profile not in memory_profile_shapes:
			raise ValueError(
				"Memory profile is not available: "
				f"{memory_type}, {memory_module_count} x "
				f"{memory_capacity_gb // memory_module_count} GB."
			)
		if (
			memory_speed_mhz is not None
			and memory_speed_mhz not in MEMORY_SPEEDS_MHZ.get(memory_type, ())
		):
			raise ValueError(
				f"{memory_speed_mhz} MHz is not a supported {memory_type} memory speed."
			)

	cpu = next((item for item in cpus if item["id"] == cpu_id), None)
	if cpu_id is not None and cpu is None:
		raise ValueError(f"CPU not found: {cpu_id}")
	selected_memory = next(
		(item for item in memory_modules if item["id"] == memory_id), None
	)
	if memory_id is not None and selected_memory is None:
		raise ValueError(f"Memory not found: {memory_id}")

	memory_profiles = []
	for profile_type, capacity_gb, module_count in memory_profile_shapes:
		capacity_per_module_gb = capacity_gb // module_count
		if cpu is None:
			compatible = None
			reasons = ["Choose a CPU to check memory compatibility."]
		else:
			candidate_boards = [
				motherboard
				for motherboard in motherboards
				if motherboard["socket"] == cpu["socket"]
				and (
					form_factor is None
					or motherboard["form_factor"] == form_factor
				)
			]
			fitting_boards = [
				motherboard
				for motherboard in candidate_boards
				if memory_profile_fits_board(
					motherboard,
					profile_type,
					capacity_gb,
					module_count,
				)
			]
			compatible = bool(fitting_boards)
			if not candidate_boards:
				location = (
					f" with {form_factor} form factor" if form_factor else ""
				)
				reasons = [
					f"No motherboard for {cpu['socket']}{location} is listed."
				]
			elif fitting_boards:
				reasons = []
			else:
				type_boards = [
					motherboard
					for motherboard in candidate_boards
					if motherboard["memory_type"] == profile_type
				]
				if not type_boards:
					reasons = [
						f"No motherboard for this CPU supports {profile_type} memory."
					]
				else:
					maximum_capacity_gb = max(
						board["max_memory_gb"] for board in type_boards
					)
					maximum_slots = max(
						board["memory_slots"] for board in type_boards
					)
					reasons = []
					if capacity_gb > maximum_capacity_gb:
						reasons.append(
							f"This {capacity_gb} GB configuration exceeds "
							f"the {maximum_capacity_gb} GB maximum on matching motherboards."
						)
					if module_count > maximum_slots:
						reasons.append(
							f"This configuration needs {module_count} memory slots, "
							f"but matching motherboards support at most {maximum_slots}."
						)
			if not reasons and not compatible:
				reasons = ["No matching motherboard supports this memory profile."]

		for speed_mhz in MEMORY_SPEEDS_MHZ.get(profile_type, ()):
			memory_profiles.append(
				{
					"memory_type": profile_type,
					"capacity_gb": capacity_gb,
					"capacity_per_module_gb": capacity_per_module_gb,
					"module_count": module_count,
					"speed_mhz": speed_mhz,
					"compatible": compatible,
					"reasons": reasons,
				}
			)

	if cpu is None:
		memory_options = [
			{
				"item": memory,
				"compatible": None,
				"reasons": ["Choose a CPU to check memory compatibility."],
			}
			for memory in memory_modules
		]
	else:
		candidate_boards = [
			motherboard
			for motherboard in motherboards
			if motherboard["socket"] == cpu["socket"]
			and (
				form_factor is None
				or motherboard["form_factor"] == form_factor
			)
		]
		memory_options = []
		for memory in memory_modules:
			if selected_profile is not None and (
				memory["memory_type"],
				memory["capacity_gb"],
				memory["modules"],
			) != selected_profile:
				continue
			if (
				memory_speed_mhz is not None
				and memory["speed_mhz"] != memory_speed_mhz
			):
				continue
			type_boards = [
				motherboard
				for motherboard in candidate_boards
				if motherboard["memory_type"] == memory["memory_type"]
			]
			fitting_boards = [
				motherboard
				for motherboard in type_boards
				if memory_profile_fits_board(
					motherboard,
					memory["memory_type"],
					memory["capacity_gb"],
					memory["modules"],
				)
			]
			reasons = []
			if not candidate_boards:
				location = f" with {form_factor} form factor" if form_factor else ""
				reasons.append(
					f"No motherboard for {cpu['socket']}{location} is listed."
				)
			elif not type_boards:
				reasons.append(
					f"No motherboard for this CPU supports {memory['memory_type']} memory."
				)
			elif not fitting_boards:
				maximum_capacity = max(
					board["max_memory_gb"] for board in type_boards
				)
				maximum_slots = max(
					board["memory_slots"] for board in type_boards
				)
				if memory["capacity_gb"] > maximum_capacity:
					reasons.append(
						f"This {memory['capacity_gb']} GB kit exceeds the "
						f"{maximum_capacity} GB maximum on matching motherboards."
					)
				if memory["modules"] > maximum_slots:
					reasons.append(
						f"This kit needs {memory['modules']} memory slots, but matching "
						f"motherboards support at most {maximum_slots}."
					)
				if not reasons:
					reasons.append("No matching motherboard supports this memory kit.")
			memory_options.append(
				{
					"item": memory,
					"compatible": bool(fitting_boards),
					"reasons": reasons,
				}
			)

	for option in memory_options:
		offer = best_offer_for_product(
			offers, "memory", option["item"]["id"]
		)
		option["price_cents"] = (
			round(
				(
					float(offer["price"])
					+ float(offer.get("shipping", 0.0))
				)
				* 100
			)
			if offer is not None
			else None
		)
		option["retailer"] = offer["retailer"] if offer is not None else None

	form_factors = sorted(
		{motherboard["form_factor"] for motherboard in motherboards}
	)
	form_factor_options = []
	for candidate_form_factor in form_factors:
		if cpu is None:
			compatible = None
			reasons = ["Choose a CPU to check motherboard form-factor compatibility."]
		else:
			compatible = any(
				motherboard["socket"] == cpu["socket"]
				and motherboard["form_factor"] == candidate_form_factor
				and (
					(
						selected_profile is None
						and selected_memory is None
					)
					or (
						selected_profile is not None
						and memory_profile_fits_board(
							motherboard,
							selected_profile[0],
							selected_profile[1],
							selected_profile[2],
						)
					)
					or (
						selected_profile is None
						and selected_memory is not None
						and memory_profile_fits_board(
							motherboard,
							selected_memory["memory_type"],
							selected_memory["capacity_gb"],
							selected_memory["modules"],
						)
					)
				)
				for motherboard in motherboards
			)
			if compatible:
				reasons = []
			elif selected_profile is not None:
				reasons = [
					f"No {candidate_form_factor} motherboard for the {cpu['socket']} "
					f"socket supports the selected {selected_profile[0]} "
					f"{selected_profile[2]} x "
					f"{selected_profile[1] // selected_profile[2]} GB "
					f"({selected_profile[1]} GB total) profile."
				]
			elif selected_memory is not None:
				reasons = [
					f"No {candidate_form_factor} motherboard for the {cpu['socket']} "
					f"socket supports the selected {selected_memory['memory_type']} "
					f"{selected_memory['capacity_gb']} GB kit."
				]
			else:
				reasons = [
					f"No {candidate_form_factor} motherboard for the "
					f"{cpu['socket']} socket is listed."
				]
		form_factor_options.append(
			{
				"value": candidate_form_factor,
				"compatible": compatible,
				"reasons": reasons,
			}
		)

	return {
		"memory": memory_options,
		"memory_profiles": memory_profiles,
		"form_factors": form_factor_options,
	}


def format_cooler_details(cooler):
	if cooler["type"] == "air":
		fit_details = f"air, {cooler['height_mm']} mm tall"
	else:
		fit_details = (
			f"AIO, {cooler['radiator_size_mm']} mm radiator, "
			f"{cooler['radiator_thickness_mm']} mm thick, "
			f"{cooler['pump_height_mm']} mm pump"
		)
	return (
		f"{cooler['name']} ({fit_details}; sockets: "
		f"{', '.join(cooler['supported_sockets'])}; "
		f"estimated max TDP {cooler['max_tdp_w']} W)"
	)


def format_build_report(
	cpu,
	gpu,
	storage,
	memory,
	motherboards,
	compatible_psus,
	cases,
	coolers_by_case,
	minimum_psu_wattage,
	offers,
	pricing_mode="cheapest",
	budget_limit=None,
	estimated_total_build_cost=0.0,
	selected_motherboard=None,
	selected_case=None,
	selected_psu=None,
):
	separator = "================================="
	lines = [
		separator,
		"Generated Build",
		separator,
		"",
		"Selected Parts:",
		f"CPU: {cpu['name']}",
		f"GPU: {gpu['name']}",
	]
	lines.extend(f"Storage: {item['name']}" for item in storage)
	lines.extend(
		[
			f"Memory: {memory['name']}",
			"",
		]
	)
	lines.extend(
		[
			"CPU:",
			cpu["name"],
			f"Socket: {cpu['socket']}",
			f"TDP: {cpu['tdp']} W",
			f"Stock cooler included: {'Yes' if cpu['stock_cooler_included'] else 'No'}",
			"",
			"GPU:",
			gpu["name"],
			f"VRAM: {gpu['vram']} GB",
			f"TDP: {gpu['tdp']} W",
			f"Length: {gpu['length_mm']} mm",
		]
	)
	if gpu.get("game_clock_mhz") is not None:
		lines.append(f"Game clock: {gpu['game_clock_mhz']} MHz")
	if gpu.get("boost_clock_mhz") is not None:
		lines.append(f"Boost clock: {gpu['boost_clock_mhz']} MHz")
	if gpu.get("oc_game_clock_mhz") is not None:
		lines.append(f"OC-mode game clock: {gpu['oc_game_clock_mhz']} MHz")
	if gpu.get("oc_boost_clock_mhz") is not None:
		lines.append(f"OC-mode boost clock: {gpu['oc_boost_clock_mhz']} MHz")
	if gpu.get("pcie_standard") is not None:
		lines.append(f"PCIe standard: {gpu['pcie_standard']}")
	if gpu.get("pcie_slot_width") is not None:
		lines.append(f"Card thickness: {gpu['pcie_slot_width']} slots")
	if gpu.get("recommended_psu_w") is not None:
		lines.append(
			f"Manufacturer recommended PSU: {gpu['recommended_psu_w']} W minimum"
		)
	for output in gpu.get("display_outputs", []):
		version = f" {output['version']}" if output.get("version") else ""
		lines.append(
			f"Display output: {output['count']} x {output['type']}{version}"
		)
	lines.append("")
	for index, item in enumerate(storage, start=1):
		lines.extend(
			[
				f"Storage {index}:",
				item["name"],
				f"Type: {item['type']}",
				f"Capacity: {item['size_gb']} GB",
				f"PCIe compatibility: {', '.join(item.get('pcie_compatibility', [])) or 'N/A'}",
				"",
			]
		)
	lines.extend(
		[
			"Memory:",
			memory["name"],
			f"Type: {memory['memory_type']}",
			f"Capacity: {memory['capacity_gb']} GB",
			f"Modules: {memory['modules']} x {memory['capacity_gb'] // memory['modules']} GB",
			f"Speed: {memory['speed_mhz']} MHz",
			"",
			"Motherboard:",
			"Compatible options:",
		]
	)
	if motherboards:
		for motherboard in motherboards:
			lines.append(
				f"- {motherboard['id']}: {motherboard['name']} "
				f"({motherboard['socket']}, {motherboard['form_factor']}, "
				f"{motherboard['memory_type']})"
			)
	else:
		lines.append("- No compatible motherboards found")

	lines.extend(
		[
			"",
			"PSU:",
			f"Estimated minimum: {minimum_psu_wattage} W "
			"(the greater of CPU TDP + GPU TDP + 200 W system allowance "
			"or the GPU manufacturer PSU recommendation)",
			"Compatible options:",
		]
	)
	if compatible_psus:
		for psu in compatible_psus:
			lines.append(
				f"- {psu['id']}: {psu['name']} "
				f"({psu['wattage']} W, {psu['efficiency']})"
			)
	else:
		lines.append("- No listed PSUs meet the estimated minimum")

	lines.extend(["", "Case:", "Compatible options:"])
	if cases:
		for case in cases:
			lines.extend(
				[
					f"- {case['name']}",
						f"  Supports: {', '.join(case['supported_motherboard_form_factors'])}",
						f"  Max GPU length: {case['max_gpu_length_mm']} mm",
						f"  Max air-cooler height: {case['max_cpu_cooler_height_mm']} mm",
						f"  Radiator support: {', '.join(str(size) for size in case['supported_radiator_sizes_mm'])} mm",
						f"  Fans: {case['included_fans']} included, {case['max_fans']} max",
				]
			)
	else:
		lines.append("- No cases fit the selected motherboard and GPU")

	lines.extend(["", "CPU Cooler:", "Compatible options by case:"])
	if cases:
		for case in cases:
			lines.append(f"{case['name']}:")
			case_coolers = coolers_by_case[case["name"]]
			if case_coolers:
				lines.extend(
					f"- {format_cooler_details(cooler)}"
					for cooler in case_coolers
				)
			else:
				lines.append("- No listed CPU coolers fit this case")
	else:
		lines.append("- No case-fit cooler options")

	lines.extend(["", "Extra Fans:"])
	if cases:
		for case in cases:
			additional_fans = max(
				0, case["max_fans"] - case["included_fans"]
			)
			lines.append(
				f"- {case['name']}: {additional_fans} additional to fill max "
				f"capacity ({case['included_fans']} included, {case['max_fans']} max)"
			)
	else:
		lines.append("- No compatible case")

	compatible = bool(
		motherboards
		and compatible_psus
		and cases
		and storage
		and memory
		and (
			cpu["stock_cooler_included"]
			or any(coolers_by_case[case["name"]] for case in cases)
		)
	)
	lines.extend(
		[
			"",
			"Pricing:",
			f"Pricing mode: {pricing_mode}",
		]
	)
	if budget_limit is not None:
		lines.append(f"Budget limit: ${budget_limit:,.2f} USD")
	lines.append(f"Estimated total build cost: ${estimated_total_build_cost:,.2f} USD")
	lines.append("Cost breakdown:")
	lines.append(f"- CPU: ${offer_total_for_component('cpu', cpu['id'], offers):,.2f} USD")
	lines.append(f"- GPU: ${offer_total_for_component('gpu', gpu['id'], offers):,.2f} USD")
	storage_total = sum(
		offer_total_for_component("storage", item["id"], offers) for item in storage
	)
	lines.append(f"- Storage: ${storage_total:,.2f} USD")
	if memory.get("id") is None:
		lines.append("- Memory: Not priced (generic profile)")
	else:
		lines.append(f"- Memory: ${offer_total_for_component('memory', memory['id'], offers):,.2f} USD")
	if memory.get("id") is None:
		lines.append("Estimated total excludes the selected generic memory profile.")
	if selected_motherboard is not None:
		lines.append(f"- Motherboard: ${offer_total_for_component('motherboard', selected_motherboard['id'], offers):,.2f} USD")
	if selected_case is not None:
		lines.append(f"- Case: ${offer_total_for_component('case', selected_case.get('id', selected_case['name']), offers):,.2f} USD")
	if selected_psu is not None:
		lines.append(f"- PSU: ${offer_total_for_component('psu', selected_psu['id'], offers):,.2f} USD")
	lines.extend(
		[
			"",
			"Compatibility:",
			"PASS" if compatible else "FAIL",
			separator,
		]
	)
	return "\n".join(lines)


def generate_build(
	cpu_id,
	gpu_id,
	storage_id=None,
	memory_id=None,
	form_factor=None,
	pricing_mode="cheapest",
	budget_limit_cents=None,
	memory_type=None,
	memory_capacity_gb=None,
	memory_module_count=None,
	memory_speed_mhz=None,
	storage_ids=None,
):
	cpus = load_json("cpus.json")
	gpus = load_json("gpus.json")
	motherboards = load_json("motherboards.json")
	cases = load_json("cases.json")
	coolers = load_json("coolers.json")
	storages = load_json("storage.json")
	memory_modules = load_json("memory.json")
	offers = load_offers()

	cpu = next((item for item in cpus if item["id"] == cpu_id), None)
	if cpu is None:
		raise ValueError(f"CPU not found: {cpu_id}")

	gpu = next((item for item in gpus if item["id"] == gpu_id), None)
	if gpu is None:
		raise ValueError(f"GPU not found: {gpu_id}")

	if storage_id is not None and storage_ids is not None:
		raise ValueError("Provide either storage_id or storage_ids, not both.")
	selected_storage_ids = (
		storage_ids if storage_ids is not None else ([storage_id] if storage_id else [])
	)
	if not selected_storage_ids:
		raise ValueError("Select at least one storage drive.")
	storage_items = []
	for selected_storage_id in selected_storage_ids:
		storage = next(
			(item for item in storages if item["id"] == selected_storage_id), None
		)
		if storage is None:
			raise ValueError(f"Storage not found: {selected_storage_id}")
		storage_items.append(storage)

	profile_values = (
		memory_type,
		memory_capacity_gb,
		memory_module_count,
		memory_speed_mhz,
	)
	has_profile_values = any(value is not None for value in profile_values)
	if memory_id is not None and has_profile_values:
		raise ValueError("Choose either a memory item or a memory profile, not both.")
	if memory_id is None:
		if not all(value is not None for value in profile_values):
			raise ValueError(
				"Provide a memory item or a complete generic memory profile."
			)
		if (
			memory_type,
			memory_capacity_gb,
			memory_module_count,
		) not in available_memory_profile_shapes():
			raise ValueError("Memory profile is not available.")
		if memory_speed_mhz not in MEMORY_SPEEDS_MHZ.get(memory_type, ()):
			raise ValueError(
				f"{memory_speed_mhz} MHz is not a supported {memory_type} memory speed."
			)
		capacity_per_module_gb = memory_capacity_gb // memory_module_count
		memory = {
			"id": None,
			"name": (
				f"{memory_type} {memory_module_count} x "
				f"{capacity_per_module_gb} GB "
				f"({memory_capacity_gb} GB total) @ {memory_speed_mhz} MHz"
			),
			"memory_type": memory_type,
			"capacity_gb": memory_capacity_gb,
			"modules": memory_module_count,
			"speed_mhz": memory_speed_mhz,
		}
	else:
		memory = next((item for item in memory_modules if item["id"] == memory_id), None)
		if memory is None:
			raise ValueError(f"Memory not found: {memory_id}")

	psus = load_json("psus.json")
	socket_motherboards = [
		motherboard
		for motherboard in motherboards
		if motherboard["socket"] == cpu["socket"]
	]
	type_motherboards = [
		motherboard
		for motherboard in socket_motherboards
		if motherboard["memory_type"] == memory["memory_type"]
	]
	capacity_motherboards = [
		motherboard
		for motherboard in type_motherboards
		if memory["capacity_gb"] <= motherboard["max_memory_gb"]
	]
	slot_motherboards = [
		motherboard
		for motherboard in type_motherboards
		if memory["modules"] <= motherboard["memory_slots"]
	]
	fitting_motherboards = [
		motherboard
		for motherboard in capacity_motherboards
		if motherboard in slot_motherboards
	]
	compatible_motherboards = [
		motherboard
		for motherboard in fitting_motherboards
		if form_factor is None or motherboard["form_factor"] == form_factor
	]

	compatible_cases = [
		case
		for case in cases
		if gpu["length_mm"] <= case["max_gpu_length_mm"]
		and any(
			motherboard["form_factor"]
			in case["supported_motherboard_form_factors"]
			for motherboard in compatible_motherboards
		)
	]
	coolers_by_case = {
		case["name"]: [
			cooler
			for cooler in coolers
			if cooler_fits_case(cooler, cpu, case)
		]
		for case in compatible_cases
	}

	calculated_psu_wattage = (
		cpu["tdp"] + gpu["tdp"] + PSU_SYSTEM_ALLOWANCE_W
	)
	minimum_psu_wattage = max(
		calculated_psu_wattage,
		gpu.get("recommended_psu_w", 0),
	)
	compatible_psus = [
		psu for psu in psus if psu["wattage"] >= minimum_psu_wattage
	]

	selected_parts = {
		"cpu": cpu,
		"gpu": gpu,
		"storage": storage_items,
		"memory": memory,
	}
	selected_part_total = sum(
		offer_total(offers, component_type, part["id"])
		for component_type, part in selected_parts.items()
		if component_type != "storage" and part["id"] is not None
	)
	selected_part_total += sum(
		offer_total(offers, "storage", storage["id"]) for storage in storage_items
	)
	selected_motherboard = None
	selected_case = None
	selected_psu = None
	if compatible_motherboards:
		selected_motherboard = min(
			compatible_motherboards,
			key=lambda motherboard: offer_total(offers, "motherboard", motherboard["id"]),
		)
		selected_part_total += offer_total(
			offers,
			"motherboard",
			selected_motherboard["id"],
		)
	if compatible_cases:
		selected_case = min(
			compatible_cases,
			key=lambda case: offer_total(offers, "case", case.get("id", case["name"])),
		)
		selected_part_total += offer_total(
			offers,
			"case",
			selected_case.get("id", selected_case["name"]),
		)
	if compatible_psus:
		selected_psu = min(compatible_psus, key=lambda psu: psu["wattage"])
		selected_part_total += offer_total(offers, "psu", selected_psu["id"])

	budget_limit = (
		budget_limit_cents / 100 if budget_limit_cents is not None else None
	)
	if pricing_mode == "budget" and budget_limit is not None:
		within_budget = round(selected_part_total * 100) <= budget_limit_cents
		if memory["id"] is None:
			budget_status = (
				"estimated partial build within budget"
				if within_budget
				else "estimated partial build over budget"
			)
		else:
			budget_status = "within budget" if within_budget else "over budget"
	else:
		budget_status = "n/a"
	selected_parts.update(
		{
			"motherboard": selected_motherboard,
			"case": selected_case,
			"psu": selected_psu,
		}
	)
	cost_breakdown = {
		component_type: offer_total(offers, component_type, part["id"])
		for component_type, part in selected_parts.items()
		if component_type != "storage"
		and part is not None
		and part["id"] is not None
	}
	cost_breakdown["storage"] = sum(
		offer_total(offers, "storage", storage["id"]) for storage in storage_items
	)
	unpriced_components = [
		component_type
		for component_type, part in selected_parts.items()
		if component_type != "storage"
		and part is not None
		and part["id"] is None
	]
	compatibility_checks = [
		{
			"code": "cpu_motherboard_socket",
			"components": ["cpu", "motherboard"],
			"status": "pass" if socket_motherboards else "fail",
			"message": (
				f"At least one listed motherboard supports the {cpu['socket']} socket."
				if socket_motherboards
				else f"No listed motherboard supports the {cpu['socket']} CPU socket."
			),
		},
	]
	if socket_motherboards:
		compatibility_checks.append(
			{
				"code": "memory_motherboard_type",
				"components": ["memory", "motherboard"],
				"status": "pass" if type_motherboards else "fail",
				"message": (
					f"At least one {cpu['socket']} motherboard supports "
					f"{memory['memory_type']} memory."
					if type_motherboards
					else f"No motherboard for the {cpu['socket']} socket supports "
					f"{memory['memory_type']} memory."
				),
			}
		)
	else:
		compatibility_checks.append(
			{
				"code": "memory_motherboard_type",
				"components": ["memory", "motherboard"],
				"status": "blocked",
				"message": "Memory compatibility cannot be checked until a matching motherboard is available.",
			}
		)
	if type_motherboards:
		maximum_memory_gb = max(
			motherboard["max_memory_gb"] for motherboard in type_motherboards
		)
		kit_capacity_gb = memory["capacity_gb"]
		compatibility_checks.append(
			{
				"code": "memory_motherboard_capacity",
				"components": ["memory", "motherboard"],
				"status": "pass" if capacity_motherboards else "fail",
				"message": (
					f"The {kit_capacity_gb} GB kit fits at least one matching motherboard."
					if capacity_motherboards
					else f"The {kit_capacity_gb} GB kit exceeds the "
					f"{maximum_memory_gb} GB maximum of matching motherboards."
				),
			}
		)
	else:
		compatibility_checks.append(
			{
				"code": "memory_motherboard_capacity",
				"components": ["memory", "motherboard"],
				"status": "blocked",
				"message": "Memory capacity cannot be checked because no motherboard supports this memory type.",
			}
		)
	if type_motherboards:
		maximum_slots = max(
			motherboard["memory_slots"] for motherboard in type_motherboards
		)
		compatibility_checks.append(
			{
				"code": "memory_motherboard_slots",
				"components": ["memory", "motherboard"],
				"status": "pass" if slot_motherboards else "fail",
				"message": (
					f"The {memory['modules']}-module kit fits at least one matching motherboard."
					if slot_motherboards
					else f"The {memory['modules']}-module kit exceeds the "
					f"{maximum_slots} memory slots on matching motherboards."
				),
			}
		)
	else:
		compatibility_checks.append(
			{
				"code": "memory_motherboard_slots",
				"components": ["memory", "motherboard"],
				"status": "blocked",
				"message": "Memory slot compatibility cannot be checked because no motherboard supports this memory type.",
			}
		)
	compatibility_checks.append(
		{
			"code": "memory_speed",
			"components": ["memory", "cpu", "motherboard"],
			"status": "unknown",
			"message": (
				f"{memory['speed_mhz']} MHz is the selected speed preference; "
				"CPU and motherboard speed limits are not modeled."
			),
		}
	)
	if form_factor is None:
		compatibility_checks.append(
			{
				"code": "motherboard_form_factor",
				"components": ["motherboard"],
				"status": "pass",
				"message": "No specific motherboard form factor was requested.",
			}
		)
	elif fitting_motherboards:
		compatibility_checks.append(
			{
				"code": "motherboard_form_factor",
				"components": ["motherboard"],
				"status": "pass" if compatible_motherboards else "fail",
				"message": (
					f"A compatible {form_factor} motherboard is available."
					if compatible_motherboards
					else f"No motherboard matching the selected CPU and memory is "
					f"available in {form_factor} form factor."
				),
			}
		)
	else:
		compatibility_checks.append(
			{
				"code": "motherboard_form_factor",
				"components": ["motherboard"],
				"status": "blocked",
				"message": "Form-factor compatibility cannot be checked until the CPU and memory have a matching motherboard.",
			}
		)

	if compatible_motherboards:
		if compatible_cases:
			case_status = "pass"
			case_message = "At least one case supports the motherboard form factor and GPU length."
		else:
			supported_cases = [
				case
				for case in cases
				if any(
					motherboard["form_factor"]
					in case["supported_motherboard_form_factors"]
					for motherboard in compatible_motherboards
				)
			]
			if supported_cases:
				maximum_gpu_length = max(
					case["max_gpu_length_mm"] for case in supported_cases
				)
				case_status = "fail"
				case_message = (
					f"The {gpu['length_mm']} mm GPU is too long for cases supporting "
					f"the selected motherboard; the maximum listed clearance is "
					f"{maximum_gpu_length} mm."
				)
			else:
				case_status = "fail"
				case_message = (
					"No listed case supports the selected motherboard form factor."
				)
	else:
		case_status = "blocked"
		case_message = "Case fit cannot be checked until a compatible motherboard is available."
	compatibility_checks.append(
		{
			"code": "gpu_case_fit",
			"components": ["gpu", "case"],
			"status": case_status,
			"message": case_message,
		}
	)

	maximum_psu_wattage = max((psu["wattage"] for psu in psus), default=0)
	compatibility_checks.append(
		{
			"code": "system_psu_wattage",
			"components": ["cpu", "gpu", "psu"],
			"status": "pass" if compatible_psus else "fail",
			"message": (
				f"A listed PSU meets the estimated {minimum_psu_wattage} W minimum"
				+ (
					f" (calculated system estimate: {calculated_psu_wattage} W; "
					f"GPU manufacturer recommendation: {gpu['recommended_psu_w']} W)."
					if gpu.get("recommended_psu_w") is not None
					else "."
				)
				if compatible_psus
				else (
					f"No listed PSU meets the estimated {minimum_psu_wattage} W "
					f"minimum (largest listed PSU: {maximum_psu_wattage} W)."
				)
			),
		}
	)
	if cpu["stock_cooler_included"]:
		cooler_status = "pass"
		cooler_message = "The CPU includes a stock cooler."
	elif not compatible_cases:
		cooler_status = "blocked"
		cooler_message = "Cooler fit cannot be checked until a compatible case is available."
	elif any(coolers_by_case[case["name"]] for case in compatible_cases):
		cooler_status = "pass"
		cooler_message = "At least one listed cooler fits a compatible case and supports the CPU."
	else:
		cooler_status = "fail"
		cooler_message = "No listed cooler fits the compatible cases and supports the CPU."
	compatibility_checks.append(
		{
			"code": "cpu_cooler_fit",
			"components": ["cpu", "cooler", "case"],
			"status": cooler_status,
			"message": cooler_message,
		}
	)
	compatibility_checks.append(
		{
			"code": "storage_motherboard_interface",
			"components": ["storage", "motherboard"],
			"status": "unknown",
			"message": (
				"Storage interface compatibility is not verified because storage "
				"interface and motherboard slot specifications are not yet modeled."
			),
		}
	)
	compatible = not any(
		check["status"] == "fail" for check in compatibility_checks
	)
	report = format_build_report(
		cpu,
		gpu,
		storage_items,
		memory,
		compatible_motherboards,
		compatible_psus,
		compatible_cases,
		coolers_by_case,
		minimum_psu_wattage,
		offers,
		pricing_mode=pricing_mode,
		budget_limit=budget_limit,
		estimated_total_build_cost=selected_part_total,
		selected_motherboard=selected_motherboard,
		selected_case=selected_case,
		selected_psu=selected_psu,
	)
	return {
		"selected_parts": {
			**selected_parts,
			"storage": (
				storage_items if storage_ids is not None else storage_items[0]
			),
		},
		"compatible_options": {
			"motherboards": compatible_motherboards,
			"psus": compatible_psus,
			"cases": compatible_cases,
			"coolers_by_case": {
				case["id"]: coolers_by_case[case["name"]]
				for case in compatible_cases
			},
		},
		"minimum_psu_wattage": minimum_psu_wattage,
		"compatible": compatible,
		"compatibility_checks": compatibility_checks,
		"pricing": {
			"mode": pricing_mode,
			"budget_limit_cents": budget_limit_cents,
			"budget_status": budget_status,
			"estimated_total_cents": round(selected_part_total * 100),
			"unpriced_components": unpriced_components,
			"cost_breakdown_cents": {
				component_type: round(amount * 100)
				for component_type, amount in cost_breakdown.items()
			},
		},
		"report": report,
	}


def main():
	parser = argparse.ArgumentParser(description="Find compatible motherboards.")
	parser.add_argument(
		"--cpu-id", "--cpu", dest="cpu_id", required=True,
		help="ID of the selected CPU",
	)
	parser.add_argument(
		"--gpu-id", "--gpu", dest="gpu_id", required=True,
		help="ID of the selected GPU",
	)
	parser.add_argument(
		"--storage-id", "--storage", dest="storage_id", required=True,
		help="ID of the selected storage drive",
	)
	parser.add_argument(
		"--memory-id", "--memory", dest="memory_id", required=True,
		help="ID of the selected memory kit",
	)
	parser.add_argument(
		"--form-factor",
		help="Optionally filter by motherboard form factor, such as ATX or Micro-ATX",
	)
	parser.add_argument(
		"--pricing-mode",
		choices=["cheapest", "budget", "balanced", "premium", "top_of_line"],
		default="cheapest",
		help="How to rank candidate build options for pricing-aware recommendations.",
	)
	parser.add_argument(
		"--budget-limit",
		type=float,
		help="Optional maximum total spend for budget mode in USD.",
	)
	arguments = parser.parse_args()
	try:
		build = generate_build(
			arguments.cpu_id,
			arguments.gpu_id,
			arguments.storage_id,
			arguments.memory_id,
			form_factor=arguments.form_factor,
			pricing_mode=arguments.pricing_mode,
			budget_limit_cents=(
				round(arguments.budget_limit * 100)
				if arguments.budget_limit is not None
				else None
			),
		)
	except ValueError as error:
		print(error)
		return 1
	print(build["report"])
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
