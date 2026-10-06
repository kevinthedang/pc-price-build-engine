import argparse
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PSU_SYSTEM_ALLOWANCE_W = 200


def load_json(filename):
	with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
		return json.load(data_file)


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
		f"Storage: {storage['name']}",
		f"Memory: {memory['name']}",
		"",
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
		"",
		"Storage:",
		storage["name"],
		f"Type: {storage['type']}",
		f"Capacity: {storage['size_gb']} GB",
		f"PCIe compatibility: {', '.join(storage.get('pcie_compatibility', [])) or 'N/A'}",
		"",
		"Memory:",
		memory["name"],
		f"Type: {memory['memory_type']}",
		f"Capacity: {memory['capacity_gb'] * memory['modules']} GB",
		f"Speed: {memory['speed_mhz']} MHz",
		"",
		"Motherboard:",
		"Compatible options:",
	]
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
			"(CPU TDP + GPU TDP + 200 W system allowance)",
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
	lines.append(f"- Storage: ${offer_total_for_component('storage', storage['id'], offers):,.2f} USD")
	lines.append(f"- Memory: ${offer_total_for_component('memory', memory['id'], offers):,.2f} USD")
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
	storage_id,
	memory_id,
	form_factor=None,
	pricing_mode="cheapest",
	budget_limit_cents=None,
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

	storage = next((item for item in storages if item["id"] == storage_id), None)
	if storage is None:
		raise ValueError(f"Storage not found: {storage_id}")

	memory = next((item for item in memory_modules if item["id"] == memory_id), None)
	if memory is None:
		raise ValueError(f"Memory not found: {memory_id}")

	psus = load_json("psus.json")
	compatible_motherboards = []
	for motherboard in motherboards:
		if motherboard["socket"] != cpu["socket"]:
			continue
		if motherboard["memory_type"] != memory["memory_type"]:
			continue
		if memory["capacity_gb"] * memory["modules"] > motherboard["max_memory_gb"]:
			continue
		if (
			form_factor is None
			or motherboard["form_factor"] == form_factor
		):
			compatible_motherboards.append(motherboard)

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

	minimum_psu_wattage = (
		cpu["tdp"] + gpu["tdp"] + PSU_SYSTEM_ALLOWANCE_W
	)
	compatible_psus = [
		psu for psu in psus if psu["wattage"] >= minimum_psu_wattage
	]

	selected_parts = {
		"cpu": cpu,
		"gpu": gpu,
		"storage": storage,
		"memory": memory,
	}
	selected_part_total = sum(
		offer_total(offers, component_type, part["id"])
		for component_type, part in selected_parts.items()
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
		budget_status = (
			"within budget"
			if round(selected_part_total * 100) <= budget_limit_cents
			else "over budget"
		)
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
		if part is not None
	}
	compatible = bool(
		compatible_motherboards
		and compatible_psus
		and compatible_cases
		and storage
		and memory
		and (
			cpu["stock_cooler_included"]
			or any(coolers_by_case[case["name"]] for case in compatible_cases)
		)
	)
	report = format_build_report(
		cpu,
		gpu,
		storage,
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
		"selected_parts": selected_parts,
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
		"pricing": {
			"mode": pricing_mode,
			"budget_limit_cents": budget_limit_cents,
			"budget_status": budget_status,
			"estimated_total_cents": round(selected_part_total * 100),
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
