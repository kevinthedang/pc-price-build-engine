-- Case clearance and fan-count limits; supported lists live in separate tables.
CREATE TABLE case_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    max_gpu_length_mm REAL NOT NULL CHECK (max_gpu_length_mm > 0),
    included_fans INTEGER NOT NULL CHECK (included_fans >= 0),
    max_fans INTEGER NOT NULL CHECK (max_fans >= included_fans),
    max_cpu_cooler_height_mm REAL NOT NULL CHECK (max_cpu_cooler_height_mm > 0)
);