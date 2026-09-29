from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class CoolerCompatibilityTests(unittest.TestCase):
    def run_app(self, cpu_id, form_factor):
        return subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                cpu_id,
                "--gpu-id",
                "gpu-000000001",
                "--form-factor",
                form_factor,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_reports_stock_cooler_and_compatible_cooling(self):
        result = self.run_app("cpu-000000007", "ATX")

        self.assertIn("Stock cooler included: Yes", result.stdout)
        self.assertIn("Thermalright Peerless Assassin 120 SE", result.stdout)
        self.assertIn("Thermalright Frozen Notte 240 BLACK ARGB", result.stdout)

    def test_case_fit_filters_air_height_and_aio_radiator(self):
        result = self.run_app("cpu-000000009", "Mini-ITX")

        self.assertIn("Stock cooler included: No", result.stdout)
        cooler_section = result.stdout.split("CPU Cooler:\n", 1)[1].split(
            "Extra Fans:\n", 1
        )[0]
        nr200p_options = cooler_section.split(
            "Cooler Master MasterBox NR200P:\n", 1
        )[1].split("Lian Li A3-mATX:", 1)[0]
        self.assertIn("Thermalright Frozen Notte 240 BLACK ARGB", nr200p_options)
        self.assertNotIn("Peerless Assassin 120 SE", nr200p_options)
        self.assertNotIn("Frozen Notte 360", nr200p_options)


if __name__ == "__main__":
    unittest.main()