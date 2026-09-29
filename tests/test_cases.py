from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class CaseCompatibilityTests(unittest.TestCase):
    def run_app(self, gpu_id, form_factor="Mini-ITX"):
        return subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000007",
                "--gpu-id",
                gpu_id,
                "--form-factor",
                form_factor,
                "--storage-id",
                "storage-000000001",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_case_filter_checks_gpu_length(self):
        result = self.run_app("gpu-000000003")

        self.assertIn("ASUS ROG STRIX B650E-I GAMING WIFI", result.stdout)
        self.assertIn("Corsair 4000D Airflow", result.stdout)
        self.assertNotIn("Cooler Master MasterBox NR200P", result.stdout)

    def test_short_gpu_fits_small_case(self):
        result = self.run_app("gpu-000000001")

        self.assertIn("Cooler Master MasterBox NR200P", result.stdout)
        self.assertIn("2 included, 7 max", result.stdout)
        self.assertIn("5 additional to fill max capacity", result.stdout)

    def test_micro_atx_build_has_compact_case_options(self):
        result = self.run_app("gpu-000000001", form_factor="Micro-ATX")

        self.assertIn("MSI MAG B650M MORTAR WIFI", result.stdout)
        self.assertIn("Lian Li A3-mATX", result.stdout)
        self.assertIn("Fractal Design Pop Mini Air", result.stdout)
        self.assertNotIn("Cooler Master MasterBox NR200P", result.stdout)


if __name__ == "__main__":
    unittest.main()