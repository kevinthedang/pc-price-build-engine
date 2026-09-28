from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class CompatibilityTests(unittest.TestCase):
    def run_app(self, cpu_id, form_factor):
        return subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                cpu_id,
                "--form-factor",
                form_factor,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_matches_socket_and_form_factor(self):
        result = self.run_app("cpu-000000002", "ATX")

        self.assertIn("ASUS TUF GAMING B550-PLUS", result.stdout)
        self.assertNotIn("MSI PRO B760-P WIFI DDR4", result.stdout)

    def test_reports_no_match(self):
        result = self.run_app("cpu-000000002", "Mini-ITX")

        self.assertIn("No compatible motherboards found.", result.stdout)


if __name__ == "__main__":
    unittest.main()