from pathlib import Path
import subprocess
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "backend" / "main.py"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import storage_interface_check  # noqa: E402

ITX_BOARD = {
    "name": "Test ITX Board",
    "sata_ports": 2,
    "m2_slots": [
        {"name": "M.2_1", "pcie_standard": "PCIe 5.0 x4", "lane_source": "CPU"},
        {"name": "M.2_2", "pcie_standard": "PCIe 4.0 x4", "lane_source": "CPU"},
    ],
}
NVME = {"name": "NVMe", "type": "NVMe SSD", "pcie_compatibility": ["PCIe 4.0 x4"]}
SATA_SSD = {"name": "SATA SSD", "type": "SATA SSD", "pcie_compatibility": []}
SATA_HDD = {"name": "SATA HDD", "type": "SATA HDD", "pcie_compatibility": []}


class StorageInterfaceCheckTests(unittest.TestCase):
    def test_passes_when_drives_fit_ports_and_slots(self):
        check = storage_interface_check([NVME, NVME, SATA_SSD, SATA_HDD], ITX_BOARD)

        self.assertEqual(check["status"], "pass")
        self.assertIn("2 of 2 SATA ports, 2 of 2 M.2 slots used", check["message"])

    def test_warns_when_sata_drives_exceed_ports(self):
        check = storage_interface_check([SATA_SSD, SATA_HDD, SATA_HDD], ITX_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn(
            "3 SATA drives selected but the Test ITX Board has 2 SATA ports",
            check["message"],
        )

    def test_warns_when_nvme_drives_exceed_m2_slots(self):
        check = storage_interface_check([NVME, NVME, NVME], ITX_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn(
            "3 NVMe drives selected but the Test ITX Board has 2 M.2 slots",
            check["message"],
        )

    def test_is_blocked_without_motherboard(self):
        check = storage_interface_check([SATA_SSD])

        self.assertEqual(check["status"], "blocked")


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
