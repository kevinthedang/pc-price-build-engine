import argparse
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename):
	with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
		return json.load(data_file)


def main():
	parser = argparse.ArgumentParser(description="Find compatible motherboards.")
	parser.add_argument("--cpu-id", required=True, help="ID of the selected CPU")
	parser.add_argument(
		"--form-factor",
		required=True,
		help="Requested motherboard form factor, such as ATX or Micro-ATX",
	)
	arguments = parser.parse_args()

	cpus = load_json("cpus.json")
	motherboards = load_json("motherboards.json")

	cpu = next((item for item in cpus if item["id"] == arguments.cpu_id), None)
	if cpu is None:
		print(f"CPU not found: {arguments.cpu_id}")
		return 1

	compatible_motherboards = []
	for motherboard in motherboards:
		if motherboard["socket"] == cpu["socket"]:
			if motherboard["form_factor"] == arguments.form_factor:
				compatible_motherboards.append(motherboard)

	if not compatible_motherboards:
		print("No compatible motherboards found.")
		return 0

	print(f"Compatible motherboards for {cpu['name']}:")
	for motherboard in compatible_motherboards:
		print(
			f"{motherboard['id']}: {motherboard['name']} "
			f"({motherboard['socket']}, {motherboard['form_factor']})"
		)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
