from pathlib import Path
import subprocess
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "backend" / "main.py"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import (  # noqa: E402
    generate_build,
    plan_storage,
    storage_interface_check,
    storage_pcie_check,
)

CPU = {
    "name": "Test CPU",
    "max_pcie_standard": "PCIe 4.0",
    "max_storage_pcie_standard": "PCIe 4.0",
}
ITX_BOARD = {
    "name": "Test ITX Board",
    "sata_ports": 2,
    "m2_slots": [
        {"name": "M.2_1", "pcie_standard": "PCIe 5.0 x4", "lane_source": "CPU", "supports_sata": False},
        {"name": "M.2_2", "pcie_standard": "PCIe 4.0 x4", "lane_source": "CPU", "supports_sata": False},
    ],
}
# Mirrors the ASUS TUF GAMING B550-PLUS: M.2_2 in SATA mode disables two SATA ports.
SHARED_PORT_BOARD = {
    "name": "Shared Port Board",
    "sata_ports": 6,
    "m2_slots": [
        {"name": "M.2_1", "pcie_standard": "PCIe 4.0 x4", "lane_source": "CPU", "supports_sata": True},
        {
            "name": "M.2_2",
            "pcie_standard": "PCIe 3.0 x4",
            "lane_source": "Chipset",
            "supports_sata": True,
            "sata_ports_disabled_in_sata_mode": 2,
        },
    ],
}
NVME = {"name": "NVMe", "type": "NVMe SSD", "form_factor": "M.2 2280", "pcie_compatibility": ["PCIe 4.0 x4"]}
M2_SATA = {"name": "M.2 SATA", "type": "SATA SSD", "form_factor": "M.2 2280", "pcie_compatibility": []}
SATA_SSD = {"name": "SATA SSD", "type": "SATA SSD", "form_factor": "2.5-inch", "pcie_compatibility": []}
SATA_HDD = {"name": "SATA HDD", "type": "SATA HDD", "form_factor": "3.5-inch", "pcie_compatibility": []}


class StorageInterfaceCheckTests(unittest.TestCase):
    def test_passes_when_drives_fit_ports_and_slots(self):
        check = storage_interface_check(CPU, [NVME, NVME, SATA_SSD, SATA_HDD], ITX_BOARD)

        self.assertEqual(check["status"], "pass")
        self.assertIn("2 of 2 SATA ports, 2 of 2 M.2 slots used", check["message"])

    def test_warns_when_sata_drives_exceed_ports(self):
        check = storage_interface_check(CPU, [SATA_SSD, SATA_HDD, SATA_HDD], ITX_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn(
            "3 SATA drives selected but the Test ITX Board has 2 SATA ports available",
            check["message"],
        )

    def test_warns_when_nvme_drives_exceed_m2_slots(self):
        check = storage_interface_check(CPU, [NVME, NVME, NVME], ITX_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn("NVMe has no free M.2 slot; the Test ITX Board has 2 M.2 slots", check["message"])

    def test_m2_sata_drive_needs_sata_capable_slot(self):
        check = storage_interface_check(CPU, [M2_SATA], ITX_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn("M.2 SATA is an M.2 SATA drive, but the Test ITX Board's M.2 slots are PCIe-only", check["message"])

    def test_m2_sata_drive_in_shared_slot_disables_sata_ports(self):
        # Both SATA-capable slots are needed, so M.2_2 runs in SATA mode and the
        # four remaining SATA ports are exactly enough for the cabled drives.
        drives = [M2_SATA, M2_SATA, *[SATA_SSD] * 4]

        check = storage_interface_check(CPU, drives, SHARED_PORT_BOARD)

        self.assertEqual(check["status"], "pass")
        self.assertIn(
            "4 of 4 SATA ports (2 ports disabled by M.2 SATA drives), 2 of 2 M.2 slots used",
            check["message"],
        )

    def test_explains_when_m2_sata_slot_would_disable_needed_ports(self):
        # Using M.2_2 would leave 4 ports for 6 cabled drives (2 unconnected), so the
        # plan leaves one M.2 SATA drive out instead (1 unconnected).
        drives = [M2_SATA, M2_SATA, *[SATA_SSD] * 6]

        check = storage_interface_check(CPU, drives, SHARED_PORT_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn(
            "M.2 SATA would need M.2_2, which disables SATA ports the other selected drives need",
            check["message"],
        )
        self.assertNotIn("SATA drives selected", check["message"])

    def test_is_blocked_without_motherboard(self):
        check = storage_interface_check(CPU, [SATA_SSD])

        self.assertEqual(check["status"], "blocked")


class StoragePlanTests(unittest.TestCase):
    def test_plan_avoids_port_disabling_slot_when_drives_would_be_left_unconnected(self):
        drives = [M2_SATA, NVME, *[SATA_SSD] * 6]

        plan = plan_storage(CPU, drives, SHARED_PORT_BOARD)

        self.assertEqual(plan["unconnected_count"], 0)
        slots_by_drive = {placement["item"]["name"]: placement["slot"]["name"] for placement in plan["placements"]}
        self.assertEqual(slots_by_drive, {"M.2 SATA": "M.2_1", "NVMe": "M.2_2"})
        self.assertEqual(plan["disabled_sata_ports"], 0)

    def test_plan_prefers_faster_slot_when_connectivity_is_equal(self):
        plan = plan_storage(CPU, [M2_SATA, NVME], SHARED_PORT_BOARD)

        slots_by_drive = {placement["item"]["name"]: placement["slot"]["name"] for placement in plan["placements"]}
        self.assertEqual(slots_by_drive, {"NVMe": "M.2_1", "M.2 SATA": "M.2_2"})
        self.assertEqual(plan["disabled_sata_ports"], 2)
        self.assertEqual(storage_pcie_check(CPU, [M2_SATA, NVME], SHARED_PORT_BOARD)["status"], "pass")


class MotherboardSelectionTests(unittest.TestCase):
    def test_selects_cheapest_board_that_fits_all_drives(self):
        # The cheapest AM5 board (MSI MAG B650M MORTAR WIFI) has 2 M.2 slots;
        # the ASUS TUF GAMING B650-PLUS has 3.
        build = generate_build(
            "cpu-000000007",
            "gpu-000000001",
            memory_id="memory-000000013",
            storage_ids=["storage-000000001"] * 3,
        )

        checks = {check["code"]: check for check in build["compatibility_checks"]}
        self.assertEqual(checks["storage_motherboard_interface"]["status"], "pass")
        self.assertIn("ASUS TUF GAMING B650-PLUS", checks["storage_motherboard_interface"]["message"])

    def test_falls_back_to_cheapest_board_when_none_fit(self):
        build = generate_build(
            "cpu-000000007",
            "gpu-000000001",
            memory_id="memory-000000013",
            storage_ids=["storage-000000003"] * 5,
        )

        checks = {check["code"]: check for check in build["compatibility_checks"]}
        self.assertEqual(checks["storage_motherboard_interface"]["status"], "warning")
        self.assertIn("MSI MAG B650M MORTAR WIFI", checks["storage_motherboard_interface"]["message"])


class StorageInterfaceReportTests(unittest.TestCase):
    def test_report_lists_sata_ports_and_m2_slots_per_motherboard(self):
        result = subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000007",
                "--gpu-id",
                "gpu-000000001",
                "--storage-id",
                "storage-000000003",
                "--memory-id",
                "memory-000000013",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn(
            "ASUS ROG STRIX B650E-I GAMING WIFI (AM5, Mini-ITX, DDR5, "
            "2 SATA ports, 2 M.2 slots)",
            result.stdout,
        )
        self.assertNotIn("SATA drive", result.stdout)


if __name__ == "__main__":
    unittest.main()
