import unittest


from fastapi.testclient import TestClient

from backend.api import CATALOG_FILES, app


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


if __name__ == "__main__":
    unittest.main()
