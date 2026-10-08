from pathlib import Path
import subprocess
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "backend" / "main.py"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import gpu_pcie_check, storage_pcie_check  # noqa: E402

RYZEN_5500 = {
    "name": "Ryzen 5 5500",
    "max_pcie_standard": "PCIe 3.0",
    "max_storage_pcie_standard": "PCIe 3.0",
}
RYZEN_5600 = {
    "name": "Ryzen 5 5600",
    "max_pcie_standard": "PCIe 4.0",
    "max_storage_pcie_standard": "PCIe 4.0",
}
CORE_I5_13600K = {
    "name": "Core i5-13600K",
    "max_pcie_standard": "PCIe 5.0",
    "max_storage_pcie_standard": "PCIe 4.0",
}
B550_BOARD = {
    "name": "Test B550",
    "pcie_x16_standard": "PCIe 4.0",
    "m2_slots": [
        {"name": "M.2_1", "pcie_standard": "PCIe 4.0 x4", "lane_source": "CPU"},
        {"name": "M.2_2", "pcie_standard": "PCIe 3.0 x4", "lane_source": "Chipset"},
    ],
}
GEN5_BOARD = {
    "name": "Test Gen5 Board",
    "pcie_x16_standard": "PCIe 5.0",
    "m2_slots": [
        {"name": "M.2_1", "pcie_standard": "PCIe 5.0 x4", "lane_source": "CPU"},
        {"name": "M.2_2", "pcie_standard": "PCIe 4.0 x4", "lane_source": "Chipset"},
    ],
}
GEN4_GPU = {"name": "Gen4 GPU", "pcie_standard": "PCIe 4.0"}
GEN5_GPU = {"name": "Gen5 GPU", "pcie_standard": "PCIe 5.0"}
GEN4_NVME = {"name": "Gen4 NVMe", "pcie_compatibility": ["PCIe 4.0 x4"]}
GEN5_NVME = {"name": "Gen5 NVMe", "pcie_compatibility": ["PCIe 5.0 x4"]}
SATA_SSD = {"name": "SATA SSD", "pcie_compatibility": []}


class PcieGenerationCliTests(unittest.TestCase):
    def run_app(self, cpu_id, gpu_id, form_factor=None):
        command = [
            sys.executable,
            str(APP_PATH),
            "--cpu-id",
            cpu_id,
            "--gpu-id",
            gpu_id,
            "--storage-id",
            "storage-000000001",
            "--memory-id",
            "memory-000000001",
        ]
        if form_factor is not None:
            command.extend(["--form-factor", form_factor])
        return subprocess.run(
            command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
        )

    def test_pcie_3_cpu_warns_for_pcie_4_gpu_and_drive(self):
        result = self.run_app("cpu-000000001", "gpu-000000006")

        self.assertIn("Compatibility:\nPASS\n", result.stdout)
        self.assertIn(
            "Warning: The PCIe 4.0 SAPPHIRE PULSE Radeon RX 7800 XT 16GB will run "
            "at PCIe 3.0 because the Ryzen 5 5500 supports up to PCIe 3.0.",
            result.stdout,
        )
        self.assertIn(
            "WD_BLACK SN850X 1TB (PCIe 4.0 x4) will run at PCIe 3.0 in M2_1 "
            "because the Ryzen 5 5500's M.2 lanes support up to PCIe 3.0.",
            result.stdout,
        )

    def test_pcie_4_cpu_and_board_have_no_pcie_warnings_for_pcie_4_parts(self):
        result = self.run_app("cpu-000000002", "gpu-000000006")

        self.assertNotIn("Warning:", result.stdout)

    def test_gen4_x16_slot_limits_pcie_5_gpu_on_intel(self):
        result = self.run_app("cpu-000000006", "gpu-000000008", "ATX")

        self.assertIn(
            "will run at PCIe 4.0 because the MSI PRO B760-P WIFI DDR4's x16 slot "
            "is PCIe 4.0.",
            result.stdout,
        )
        self.assertNotIn("Core i5-13600K supports up to", result.stdout)


class GpuPcieCheckTests(unittest.TestCase):
    def test_passes_when_cpu_and_slot_match_gpu(self):
        check = gpu_pcie_check(CORE_I5_13600K, GEN5_GPU, GEN5_BOARD)

        self.assertEqual(check["code"], "gpu_pcie_generation")
        self.assertEqual(check["status"], "pass")

    def test_names_both_cpu_and_slot_when_both_limit(self):
        board = {**B550_BOARD, "pcie_x16_standard": "PCIe 3.0"}

        check = gpu_pcie_check(RYZEN_5500, GEN4_GPU, board)

        self.assertEqual(check["status"], "warning")
        self.assertIn("Ryzen 5 5500 supports up to PCIe 3.0", check["message"])
        self.assertIn("Test B550's x16 slot is PCIe 3.0", check["message"])

    def test_falls_back_to_cpu_limit_without_motherboard(self):
        check = gpu_pcie_check(RYZEN_5500, GEN4_GPU)

        self.assertEqual(check["status"], "warning")

    def test_is_unknown_without_gpu_pcie_data(self):
        check = gpu_pcie_check(RYZEN_5500, {"name": "Test GPU"}, B550_BOARD)

        self.assertEqual(check["status"], "unknown")


class StoragePcieCheckTests(unittest.TestCase):
    def test_second_drive_is_limited_by_chipset_slot(self):
        check = storage_pcie_check(RYZEN_5600, [GEN4_NVME, GEN4_NVME], B550_BOARD)

        self.assertEqual(check["code"], "storage_pcie_generation")
        self.assertEqual(check["status"], "warning")
        self.assertEqual(
            check["message"],
            "Gen4 NVMe (PCIe 4.0 x4) will run at PCIe 3.0 in M.2_2 because "
            "M.2_2 on the Test B550 is PCIe 3.0.",
        )

    def test_intel_cpu_m2_lanes_limit_gen5_drive_in_cpu_slot(self):
        check = storage_pcie_check(CORE_I5_13600K, [GEN5_NVME], GEN5_BOARD)

        self.assertEqual(check["status"], "warning")
        self.assertIn("will run at PCIe 4.0 in M.2_1", check["message"])
        self.assertIn("Core i5-13600K's M.2 lanes support up to PCIe 4.0", check["message"])

    def test_chipset_slot_is_not_limited_by_cpu(self):
        board = {
            "name": "Chipset Only",
            "pcie_x16_standard": "PCIe 4.0",
            "m2_slots": [
                {"name": "M.2_1", "pcie_standard": "PCIe 4.0 x4", "lane_source": "Chipset"}
            ],
        }

        check = storage_pcie_check(RYZEN_5500, [GEN4_NVME], board)

        self.assertEqual(check["status"], "pass")

    def test_fastest_drive_gets_fastest_slot(self):
        check = storage_pcie_check(
            {**RYZEN_5600, "max_storage_pcie_standard": "PCIe 5.0"},
            [GEN4_NVME, GEN5_NVME],
            GEN5_BOARD,
        )

        self.assertEqual(check["status"], "pass")

    def test_drives_without_free_m2_slot_are_left_to_interface_check(self):
        check = storage_pcie_check(RYZEN_5600, [GEN4_NVME] * 3, B550_BOARD)

        self.assertNotIn("no free M.2 slot", check["message"])
        self.assertEqual(check["message"].count("Gen4 NVMe"), 1)

    def test_passes_for_sata_only_builds(self):
        check = storage_pcie_check(RYZEN_5500, [SATA_SSD], B550_BOARD)

        self.assertEqual(check["status"], "pass")


if __name__ == "__main__":
    unittest.main()
