from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class PsuRecommendationTests(unittest.TestCase):
    def test_cpu_gpu_pair_finds_sufficient_psu(self):
        result = subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000009",
                "--gpu-id",
                "gpu-000000004",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("Estimated minimum: 770 W", result.stdout)
        self.assertIn("Corsair RM850x (2021)", result.stdout)
        self.assertNotIn("Corsair RM750x (2021)", result.stdout)
        self.assertNotIn("MSI MAG A650BN", result.stdout)


if __name__ == "__main__":
    unittest.main()