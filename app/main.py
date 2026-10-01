import argparse
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PSU_SYSTEM_ALLOWANCE_W = 200


def load_json(filename):
	with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
		return json.load(data_file)


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
):
	separator = "================================="
	lines = [
		separator,
		"Generated Build",
		separator,
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
			"Compatibility:",
			"PASS" if compatible else "FAIL",
			separator,
		]
	)
	return "\n".join(lines)


def main():
	parser = argparse.ArgumentParser(description="Find compatible motherboards.")
	parser.add_argument(
		"--cpu-id",
		"--cpu",
		dest="cpu_id",
		required=True,
		help="ID of the selected CPU",
	)
	parser.add_argument(
		"--gpu-id",
		"--gpu",
		dest="gpu_id",
		required=True,
		help="ID of the selected GPU",
	)
	parser.add_argument(
		"--storage-id",
		"--storage",
		dest="storage_id",
		required=True,
		help="ID of the selected storage drive",
	)
	parser.add_argument(
		"--memory-id",
		"--memory",
		dest="memory_id",
		required=True,
		help="ID of the selected memory kit",
	)
	parser.add_argument(
		"--form-factor",
		help="Optionally filter by motherboard form factor, such as ATX or Micro-ATX",
	)
	arguments = parser.parse_args()

	cpus = load_json("cpus.json")
	gpus = load_json("gpus.json")
	motherboards = load_json("motherboards.json")
	cases = load_json("cases.json")
	coolers = load_json("coolers.json")
	storages = load_json("storage.json")
	memory_modules = load_json("memory.json")

	cpu = next((item for item in cpus if item["id"] == arguments.cpu_id), None)
	if cpu is None:
		print(f"CPU not found: {arguments.cpu_id}")
		return 1

	gpu = next((item for item in gpus if item["id"] == arguments.gpu_id), None)
	if gpu is None:
		print(f"GPU not found: {arguments.gpu_id}")
		return 1

	storage = next((item for item in storages if item["id"] == arguments.storage_id), None)
	if storage is None:
		print(f"Storage not found: {arguments.storage_id}")
		return 1

	memory = next((item for item in memory_modules if item["id"] == arguments.memory_id), None)
	if memory is None:
		print(f"Memory not found: {arguments.memory_id}")
		return 1

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
			arguments.form_factor is None
			or motherboard["form_factor"] == arguments.form_factor
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
	print(
		format_build_report(
			cpu,
			gpu,
			storage,
			memory,
			compatible_motherboards,
			compatible_psus,
			compatible_cases,
			coolers_by_case,
			minimum_psu_wattage,
		)
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
