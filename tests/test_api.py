import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import CATALOG_FILES, app
from backend.main import load_json


class BuildApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_catalog_index_and_component_catalogs(self):
        response = self.client.get("/api/catalogs")

        self.assertEqual(response.status_code, 200)
        catalogs = response.json()["catalogs"]
        self.assertEqual({entry["name"] for entry in catalogs}, set(CATALOG_FILES))
        for catalog_name in CATALOG_FILES:
            with self.subTest(catalog=catalog_name):
                catalog_response = self.client.get(f"/api/catalogs/{catalog_name}")
                self.assertEqual(catalog_response.status_code, 200)
                self.assertIsInstance(catalog_response.json(), list)

    def test_generate_build_returns_structured_build_and_cent_pricing(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "storage_id": "storage-000000001",
                "memory_id": "memory-000000003",
                "form_factor": "ATX",
                "mode": "budget",
                "budget_limit_cents": 150000,
            },
        )

        self.assertEqual(response.status_code, 200)
        build = response.json()
        self.assertEqual(build["selected_parts"]["cpu"]["id"], "cpu-000000002")
        self.assertIn("Capacity: 16 GB", build["report"])
        self.assertEqual(build["pricing"]["mode"], "budget")
        self.assertEqual(build["pricing"]["budget_limit_cents"], 150000)
        self.assertIsInstance(build["pricing"]["estimated_total_cents"], int)
        self.assertEqual(
            build["pricing"]["budget_status"],
            "within budget"
            if build["pricing"]["estimated_total_cents"] <= 150000
            else "over budget",
        )
        self.assertIn("Motherboard:", build["report"])
        self.assertIn("memory", build["pricing"]["cost_breakdown_cents"])
        self.assertNotIn("memory", build["pricing"]["unpriced_components"])

    def test_asus_gpu_recommendation_sets_system_psu_minimum(self):
        catalog_response = self.client.get("/api/catalogs/gpus")
        asus_gpu = next(
            gpu for gpu in catalog_response.json() if gpu["id"] == "gpu-000000008"
        )
        self.assertEqual(asus_gpu["pcie_standard"], "PCIe 5.0")
        self.assertEqual(asus_gpu["recommended_psu_w"], 750)
        self.assertEqual(asus_gpu["pcie_slot_width"], 2.5)
        self.assertEqual(
            asus_gpu["display_outputs"],
            [
                {"type": "HDMI", "version": "2.1b", "count": 1},
                {"type": "DisplayPort", "version": "2.1a", "count": 3},
            ],
        )

        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": asus_gpu["id"],
                "storage_id": "storage-000000001",
                "memory_id": "memory-000000003",
            },
        )

        self.assertEqual(response.status_code, 200)
        build = response.json()
        self.assertEqual(build["minimum_psu_wattage"], 750)
        psu_check = next(
            check
            for check in build["compatibility_checks"]
            if check["code"] == "system_psu_wattage"
        )
        self.assertIn("calculated system estimate: 569 W", psu_check["message"])
        self.assertIn("GPU manufacturer recommendation: 750 W", psu_check["message"])
        self.assertIn("Estimated minimum: 750 W", build["report"])
        self.assertIn("Card thickness: 2.5 slots", build["report"])
        self.assertIn("OC-mode boost clock: 3030 MHz", build["report"])
        self.assertIn("Display output: 1 x HDMI 2.1b", build["report"])
        self.assertIn("Display output: 3 x DisplayPort 2.1a", build["report"])

    def test_calculated_psu_requirement_can_exceed_gpu_recommendation(self):
        def load_catalog(filename):
            catalog = load_json(filename)
            if filename == "gpus.json":
                gpu_4090 = next(
                    gpu for gpu in catalog if gpu["id"] == "gpu-000000004"
                )
                gpu_4090["recommended_psu_w"] = 500
            return catalog

        with patch("backend.main.load_json", side_effect=load_catalog):
            response = self.client.post(
                "/api/builds/generate",
                json={
                    "cpu_id": "cpu-000000009",
                    "gpu_id": "gpu-000000004",
                    "storage_id": "storage-000000001",
                    "memory_id": "memory-000000007",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["minimum_psu_wattage"], 770)

    def test_generate_build_includes_and_prices_multiple_storage_drives(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "storage_ids": ["storage-000000001", "storage-000000002"],
                "memory_id": "memory-000000003",
            },
        )

        self.assertEqual(response.status_code, 200)
        build = response.json()
        self.assertEqual(
            [part["id"] for part in build["selected_parts"]["storage"]],
            ["storage-000000001", "storage-000000002"],
        )
        self.assertEqual(build["pricing"]["cost_breakdown_cents"]["storage"], 25697)
        self.assertIn("Storage 1:", build["report"])
        self.assertIn("Storage 2:", build["report"])

    def test_generation_requires_at_least_one_storage_drive(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "memory_id": "memory-000000003",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Select at least one storage drive.")

    def test_generate_build_accepts_generic_memory_profile_without_pricing_it(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "storage_id": "storage-000000001",
                "memory_type": "DDR4",
                "memory_capacity_gb": 16,
                "memory_module_count": 2,
                "memory_speed_mhz": 3200,
                "form_factor": "ATX",
            },
        )

        self.assertEqual(response.status_code, 200)
        build = response.json()
        memory = build["selected_parts"]["memory"]
        self.assertIsNone(memory["id"])
        self.assertEqual(memory["memory_type"], "DDR4")
        self.assertEqual(memory["capacity_gb"], 16)
        self.assertEqual(memory["modules"], 2)
        self.assertEqual(memory["speed_mhz"], 3200)
        self.assertIn("memory", build["pricing"]["unpriced_components"])
        self.assertNotIn("memory", build["pricing"]["cost_breakdown_cents"])
        self.assertIn("Memory: Not priced (generic profile)", build["report"])
        checks = {check["code"]: check for check in build["compatibility_checks"]}
        self.assertEqual(checks["memory_motherboard_slots"]["status"], "pass")
        self.assertEqual(checks["memory_speed"]["status"], "unknown")

    def test_generation_rejects_generic_memory_speed_from_another_generation(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "storage_id": "storage-000000001",
                "memory_type": "DDR4",
                "memory_capacity_gb": 16,
                "memory_module_count": 2,
                "memory_speed_mhz": 6000,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("not a supported DDR4 memory speed", response.json()["detail"])

    def test_generation_rejects_unknown_component_ids(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-999999999",
                "gpu_id": "gpu-000000001",
                "storage_id": "storage-000000001",
                "memory_id": "memory-000000003",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "CPU not found: cpu-999999999")

    def test_generation_validates_mode_and_budget(self):
        request = {
            "cpu_id": "cpu-000000002",
            "gpu_id": "gpu-000000001",
            "storage_id": "storage-000000001",
            "memory_id": "memory-000000003",
        }

        invalid_mode = self.client.post(
            "/api/builds/generate", json={**request, "mode": "performance"}
        )
        negative_budget = self.client.post(
            "/api/builds/generate",
            json={**request, "budget_limit_cents": -1},
        )

        self.assertEqual(invalid_mode.status_code, 422)
        self.assertEqual(negative_budget.status_code, 422)

    def test_options_explain_memory_and_form_factor_compatibility(self):
        response = self.client.get(
            "/api/builds/options",
            params={"cpu_id": "cpu-000000002"},
        )

        self.assertEqual(response.status_code, 200)
        options = response.json()
        memory_options = {
            option["item"]["id"]: option for option in options["memory"]
        }
        self.assertTrue(memory_options["memory-000000003"]["compatible"])
        self.assertFalse(memory_options["memory-000000007"]["compatible"])
        self.assertIn(
            "DDR5",
            memory_options["memory-000000007"]["reasons"][0],
        )
        self.assertEqual(memory_options["memory-000000001"]["price_cents"], 3999)
        self.assertEqual(memory_options["memory-000000001"]["retailer"], "amazon")
        form_factors = {
            option["value"]: option for option in options["form_factors"]
        }
        self.assertTrue(form_factors["ATX"]["compatible"])
        self.assertFalse(form_factors["Mini-ITX"]["compatible"])

    def test_memory_profiles_are_generic_and_checked_against_cpu_motherboards(self):
        response = self.client.get(
            "/api/builds/options",
            params={"cpu_id": "cpu-000000002"},
        )

        self.assertEqual(response.status_code, 200)
        options = response.json()
        profiles = {
            (
                profile["memory_type"],
                profile["capacity_gb"],
                profile["module_count"],
                profile["speed_mhz"],
            ): profile
            for profile in options["memory_profiles"]
        }
        ddr4_profile = profiles[("DDR4", 16, 2, 3200)]
        ddr5_profile = profiles[("DDR5", 32, 2, 4800)]
        self.assertTrue(ddr4_profile["compatible"])
        self.assertEqual(ddr4_profile["capacity_per_module_gb"], 8)
        self.assertFalse(ddr5_profile["compatible"])
        self.assertIn(
            ("DDR4", 16, 2, 4000),
            profiles,
        )
        self.assertIn(
            ("DDR5", 32, 2, 8000),
            profiles,
        )
        self.assertIn(("DDR5", 36, 2, 6000), profiles)
        self.assertIn(("DDR5", 96, 3, 6000), profiles)
        self.assertIn("DDR5", ddr5_profile["reasons"][0])
        self.assertNotIn("id", ddr4_profile)
        self.assertNotIn("name", ddr4_profile)

    def test_selected_memory_profile_filters_form_factor_compatibility(self):
        response = self.client.get(
            "/api/builds/options",
            params={
                "cpu_id": "cpu-000000002",
                "memory_type": "DDR4",
                "memory_capacity_gb": 32,
                "memory_module_count": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        form_factors = {
            option["value"]: option for option in response.json()["form_factors"]
        }
        self.assertTrue(form_factors["ATX"]["compatible"])
        self.assertFalse(form_factors["Mini-ITX"]["compatible"])

    def test_selected_memory_profile_returns_exact_catalog_memory_matches(self):
        response = self.client.get(
            "/api/builds/options",
            params={
                "cpu_id": "cpu-000000002",
                "memory_type": "DDR4",
                "memory_capacity_gb": 16,
                "memory_module_count": 2,
                "memory_speed_mhz": 3200,
            },
        )

        self.assertEqual(response.status_code, 200)
        memory = response.json()["memory"]
        self.assertEqual(
            {option["item"]["id"] for option in memory},
            {"memory-000000001", "memory-000000005"},
        )
        self.assertTrue(all(option["compatible"] for option in memory))

    def test_memory_kit_capacity_is_total_across_modules(self):
        response = self.client.get(
            "/api/builds/options",
            params={
                "cpu_id": "cpu-000000005",
                "form_factor": "Mini-ITX",
                "memory_type": "DDR5",
                "memory_capacity_gb": 64,
                "memory_module_count": 2,
                "memory_speed_mhz": 4800,
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = next(
            profile
            for profile in response.json()["memory_profiles"]
            if profile["memory_type"] == "DDR5"
            and profile["capacity_gb"] == 64
            and profile["module_count"] == 2
            and profile["speed_mhz"] == 4800
        )
        self.assertTrue(profile["compatible"])
        self.assertEqual(profile["capacity_per_module_gb"], 32)

    def test_memory_profiles_reject_partial_or_unavailable_profiles(self):
        partial_profile = self.client.get(
            "/api/builds/options",
            params={"memory_type": "DDR4"},
        )
        unavailable_profile = self.client.get(
            "/api/builds/options",
            params={
                "memory_type": "DDR4",
                "memory_capacity_gb": 128,
                "memory_module_count": 2,
                "memory_speed_mhz": 3200,
            },
        )

        self.assertEqual(partial_profile.status_code, 404)
        self.assertEqual(unavailable_profile.status_code, 404)

    def test_memory_profile_rejects_speed_from_another_memory_generation(self):
        response = self.client.get(
            "/api/builds/options",
            params={
                "memory_type": "DDR4",
                "memory_capacity_gb": 16,
                "memory_module_count": 2,
                "memory_speed_mhz": 6000,
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_generation_explains_known_failure_and_unmodeled_storage(self):
        response = self.client.post(
            "/api/builds/generate",
            json={
                "cpu_id": "cpu-000000002",
                "gpu_id": "gpu-000000001",
                "storage_id": "storage-000000001",
                "memory_id": "memory-000000007",
            },
        )

        self.assertEqual(response.status_code, 200)
        build = response.json()
        self.assertFalse(build["compatible"])
        checks = {check["code"]: check for check in build["compatibility_checks"]}
        self.assertEqual(checks["memory_motherboard_type"]["status"], "fail")
        self.assertIn("DDR5", checks["memory_motherboard_type"]["message"])
        self.assertEqual(checks["storage_motherboard_interface"]["status"], "unknown")


class WorkerCatalogCacheTests(unittest.TestCase):
    def test_load_json_uses_worker_catalog_cache(self):
        with patch(
            "backend.main._worker_catalogs",
            {"cpus.json": '[{"id": "worker-cpu"}]'},
        ):
            self.assertEqual(load_json("cpus.json"), [{"id": "worker-cpu"}])

    def test_missing_worker_catalog_raises_file_not_found(self):
        with patch("backend.main._worker_catalogs", {}):
            with self.assertRaises(FileNotFoundError):
                load_json("missing.json")


if __name__ == "__main__":
    unittest.main()
