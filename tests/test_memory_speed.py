from pathlib import Path
import subprocess
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "backend" / "main.py"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import memory_speed_check  # noqa: E402


class MemorySpeedCheckTests(unittest.TestCase):
    def run_app(self, cpu_id, memory_id):
        return subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                cpu_id,
                "--gpu-id",
                "gpu-000000001",
                "--storage-id",
                "storage-000000001",
                "--memory-id",
                memory_id,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_memory_above_cpu_rated_speed_adds_report_warning(self):
        result = self.run_app("cpu-000000007", "memory-000000007")

        self.assertIn("Compatibility:\nPASS\nWarning: The 6000 MHz DDR5 memory", result.stdout)
        self.assertIn("Ryzen 5 7600's rated maximum of DDR5-5200", result.stdout)

    def test_ddr4_above_cpu_rated_speed_adds_report_warning(self):
        result = self.run_app("cpu-000000002", "memory-000000003")

        self.assertIn("Warning: The 3600 MHz DDR4 memory", result.stdout)
        self.assertIn("DDR4-3200", result.stdout)

    def test_memory_at_cpu_rated_speed_has_no_warning(self):
        result = self.run_app("cpu-000000002", "memory-000000001")

        self.assertNotIn("Warning:", result.stdout)

    def test_check_uses_rated_speed_for_selected_memory_type(self):
        cpu = {
            "name": "Core i5-13600K",
            "max_memory_speeds": [
                {"memory_type": "DDR5", "max_speed_mhz": 5600},
                {"memory_type": "DDR4", "max_speed_mhz": 3200},
            ],
        }

        ddr5 = memory_speed_check(cpu, {"memory_type": "DDR5", "speed_mhz": 5600})
        ddr4 = memory_speed_check(cpu, {"memory_type": "DDR4", "speed_mhz": 3600})

        self.assertEqual(ddr5["status"], "pass")
        self.assertEqual(ddr4["status"], "warning")

    def test_check_is_blocked_when_cpu_has_no_rating_for_memory_type(self):
        cpu = {
            "name": "Ryzen 5 7600",
            "max_memory_speeds": [{"memory_type": "DDR5", "max_speed_mhz": 5200}],
        }

        check = memory_speed_check(cpu, {"memory_type": "DDR4", "speed_mhz": 3200})

        self.assertEqual(check["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
