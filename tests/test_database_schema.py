from pathlib import Path
import json
import sqlite3
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRS = (
    PROJECT_ROOT / "database" / "core",
    PROJECT_ROOT / "database" / "specs",
)
SCHEMA_FILES = sorted(
    (schema_file for directory in SCHEMA_DIRS for schema_file in directory.glob("*.sql")),
    key=lambda schema_file: schema_file.name,
)
CATALOG_FILES = (
    "cpus.json",
    "gpus.json",
    "storage.json",
    "memory.json",
    "motherboards.json",
    "cases.json",
    "coolers.json",
    "psus.json",
)


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys = ON")
        for schema_file in SCHEMA_FILES:
            self.connection.executescript(
                schema_file.read_text(encoding="utf-8")
            )

    def tearDown(self):
        self.connection.close()

    def test_schema_creates_component_and_offer_tables(self):
        tables = {
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        self.assertIn("products", tables)
        self.assertIn("cpu_specs", tables)
        self.assertIn("cpu_memory_speeds", tables)
        self.assertIn("gpu_specs", tables)
        self.assertIn("gpu_display_outputs", tables)
        self.assertIn("case_specs", tables)
        self.assertIn("offers", tables)

    def test_each_sql_file_creates_one_table(self):
        table_count = self.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]

        self.assertEqual(table_count, len(SCHEMA_FILES))

    def test_cpu_specs_includes_core_thread_and_clock_fields(self):
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(cpu_specs)")
        }

        self.assertTrue(
            {
                "core_count",
                "thread_count",
                "performance_core_count",
                "efficiency_core_count",
                "base_clock_mhz",
                "efficiency_core_base_clock_mhz",
                "max_clock_mhz",
                "max_clock_type",
                "max_pcie_standard",
            }.issubset(columns)
        )

    def test_cpu_catalog_records_max_pcie_standard(self):
        cpus = json.loads(
            (PROJECT_ROOT / "data" / "cpus.json").read_text(encoding="utf-8")
        )
        for cpu in cpus:
            with self.subTest(cpu=cpu["name"]):
                self.assertRegex(cpu.get("max_pcie_standard", ""), r"^PCIe \d\.0$")

        ryzen_5500 = next(cpu for cpu in cpus if cpu["name"] == "Ryzen 5 5500")
        self.assertEqual(ryzen_5500["max_pcie_standard"], "PCIe 3.0")

    def test_cpu_memory_speeds_are_unique_per_memory_type(self):
        columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(cpu_memory_speeds)"
            )
        }
        self.assertTrue(
            {"product_id", "memory_type", "max_speed_mhz"}.issubset(columns)
        )

        self.connection.execute(
            "INSERT INTO products (id, product_type, name) "
            "VALUES ('cpu-test', 'cpu', 'Test CPU')"
        )
        insert = (
            "INSERT INTO cpu_memory_speeds (product_id, memory_type, max_speed_mhz) "
            "VALUES ('cpu-test', 'DDR5', ?)"
        )
        self.connection.execute(insert, (5600,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(insert, (4800,))

    def test_cpu_catalog_records_max_memory_speed_per_type(self):
        cpus = json.loads(
            (PROJECT_ROOT / "data" / "cpus.json").read_text(encoding="utf-8")
        )
        for cpu in cpus:
            with self.subTest(cpu=cpu["name"]):
                speeds = cpu.get("max_memory_speeds")
                self.assertTrue(speeds)
                memory_types = [speed["memory_type"] for speed in speeds]
                self.assertEqual(len(memory_types), len(set(memory_types)))
                for speed in speeds:
                    self.assertIn(speed["memory_type"], {"DDR4", "DDR5"})
                    self.assertGreater(speed["max_speed_mhz"], 0)

        i5_13600k = next(cpu for cpu in cpus if cpu["name"] == "Core i5-13600K")
        self.assertEqual(
            i5_13600k["max_memory_speeds"],
            [
                {"memory_type": "DDR5", "max_speed_mhz": 5600},
                {"memory_type": "DDR4", "max_speed_mhz": 3200},
            ],
        )

    def test_gpu_specs_includes_clocks_pcie_and_power_fields(self):
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(gpu_specs)")
        }

        self.assertTrue(
            {
                "game_clock_mhz",
                "boost_clock_mhz",
                "oc_game_clock_mhz",
                "oc_boost_clock_mhz",
                "pcie_standard",
                "recommended_psu_w",
                "pcie_slot_width",
            }.issubset(columns)
        )

    def test_gpu_display_outputs_stores_versioned_connector_counts(self):
        columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(gpu_display_outputs)"
            )
        }

        self.assertTrue(
            {
                "product_id",
                "output_type",
                "version",
                "output_count",
            }.issubset(columns)
        )

    def test_component_catalogs_have_product_ids_and_names(self):
        for filename in CATALOG_FILES:
            records = json.loads(
                (PROJECT_ROOT / "data" / filename).read_text(encoding="utf-8")
            )
            for record in records:
                with self.subTest(catalog=filename, product=record.get("name")):
                    self.assertTrue(record.get("id"))
                    self.assertTrue(record.get("name"))

    def test_offer_requires_an_existing_product(self):
        self.connection.execute("INSERT INTO retailers (name) VALUES ('Example')")

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """INSERT INTO offers (
                    offer_id, product_id, retailer_id, price_cents, availability,
                    condition, checked_at
                ) VALUES ('offer-1', 'missing-product', 1, 1000, 'in_stock', 'new', '2026-10-01T12:00:00Z')"""
            )


if __name__ == "__main__":
    unittest.main()
