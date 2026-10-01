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
        self.assertIn("gpu_specs", tables)
        self.assertIn("case_specs", tables)
        self.assertIn("offers", tables)

    def test_each_sql_file_creates_one_table(self):
        table_count = self.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]

        self.assertEqual(table_count, len(SCHEMA_FILES))

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
