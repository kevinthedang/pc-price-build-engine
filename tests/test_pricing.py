from pathlib import Path
import json
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app" / "main.py"


class PricingModeTests(unittest.TestCase):
    def run_app(self, pricing_mode="budget", budget_limit="1200"):
        return subprocess.run(
            [
                sys.executable,
                str(APP_PATH),
                "--cpu-id",
                "cpu-000000002",
                "--gpu-id",
                "gpu-000000001",
                "--storage-id",
                "storage-000000001",
                "--memory-id",
                "memory-000000003",
                "--form-factor",
                "ATX",
                "--pricing-mode",
                pricing_mode,
                "--budget-limit",
                budget_limit,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_budget_mode_reports_pricing_summary(self):
        result = self.run_app("budget", "1200")

        self.assertIn("Pricing mode: budget", result.stdout)
        self.assertIn("Budget limit: $1,200.00 USD", result.stdout)
        self.assertIn("Estimated total build cost:", result.stdout)

    def test_top_of_line_mode_is_supported(self):
        result = self.run_app("top_of_line", "2000")

        self.assertIn("Pricing mode: top_of_line", result.stdout)
        self.assertIn("Estimated total build cost:", result.stdout)

    def test_selected_parts_are_listed(self):
        result = self.run_app("budget", "1200")

        self.assertIn("Selected Parts:", result.stdout)
        self.assertIn("CPU: Ryzen 5 5600", result.stdout)
        self.assertIn("GPU: Gigabyte GeForce RTX 4060 WINDFORCE OC 8G", result.stdout)
        self.assertIn("Storage: WD_BLACK SN850X 1TB", result.stdout)
        self.assertIn("Memory: G.Skill Ripjaws V 16GB", result.stdout)

    def test_case_offers_match_case_ids(self):
        cases = json.loads((PROJECT_ROOT / "data" / "cases.json").read_text())
        offers = json.loads((PROJECT_ROOT / "data" / "offers.json").read_text())

        case_ids = {case["id"] for case in cases if "id" in case}
        matched_case_offers = {
            offer["product_id"]
            for offer in offers
            if offer.get("component_type") == "case"
        }

        self.assertTrue(matched_case_offers.issubset(case_ids))


if __name__ == "__main__":
    unittest.main()
