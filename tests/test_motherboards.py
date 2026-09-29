from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class MotherboardCompatibilityTests(unittest.TestCase):
    def run_app(self, cpu_id, form_factor=None, gpu_id="gpu-000000001"):
        command = [
            sys.executable,
            str(APP_PATH),
            "--cpu-id",
            cpu_id,
            "--gpu-id",
            gpu_id,
            "--storage-id",
            "storage-000000001",
        ]
        if form_factor is not None:
            command.extend(["--form-factor", form_factor])

        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_matches_socket_and_form_factor(self):
        result = self.run_app("cpu-000000002", "ATX")

        self.assertIn(
            "GPU:\nGigabyte GeForce RTX 4060 WINDFORCE OC 8G",
            result.stdout,
        )
        self.assertIn("ASUS TUF GAMING B550-PLUS", result.stdout)
        self.assertNotIn("MSI PRO B760-P WIFI DDR4", result.stdout)

    def test_lists_all_socket_matches_without_form_factor(self):
        result = self.run_app("cpu-000000002")

        self.assertIn("ASUS TUF GAMING B550-PLUS", result.stdout)
        self.assertIn("MSI MAG B550M MORTAR WIFI", result.stdout)
        self.assertNotIn("MSI PRO B760-P WIFI DDR4", result.stdout)
        self.assertIn("MSI MAG A650BN", result.stdout)

    def test_reports_no_match(self):
        result = self.run_app("cpu-000000002", "Mini-ITX")

        self.assertIn("No compatible motherboards found", result.stdout)

    def test_requires_gpu_argument(self):
        result = subprocess.run(
            [sys.executable, str(APP_PATH), "--cpu-id", "cpu-000000002"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--gpu-id", result.stderr)

    def test_rejects_unknown_gpu(self):
        result = subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000002",
                "--gpu-id",
                "gpu-999999999",
                "--storage-id",
                "storage-000000001",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("GPU not found: gpu-999999999", result.stdout)

    def test_gpu_alias_accepts_id(self):
        result = subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000002",
                "--gpu",
                "gpu-000000001",
                "--storage-id",
                "storage-000000001",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn(
            "GPU:\nGigabyte GeForce RTX 4060 WINDFORCE OC 8G",
            result.stdout,
        )

    def test_generated_report_sections_are_ordered(self):
        result = self.run_app("cpu-000000002")
        section_names = [
            "CPU:",
            "GPU:",
            "Motherboard:",
            "PSU:",
            "Case:",
            "CPU Cooler:",
            "Extra Fans:",
            "Compatibility:",
        ]

        section_positions = [result.stdout.index(name) for name in section_names]
        self.assertEqual(section_positions, sorted(section_positions))


if __name__ == "__main__":
    unittest.main()